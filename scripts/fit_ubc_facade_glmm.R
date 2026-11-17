#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(glmmTMB)
  library(DHARMa)
  library(jsonlite)
})

parse_args <- function(args) {
  result <- list(
    input = "data/derived/ubc/ubc_facade_survey_panel.csv",
    audit = "data/derived/ubc/ubc_facade_panel_audit.json",
    out_dir = "results/ubc"
  )
  i <- 1
  while (i <= length(args)) {
    key <- args[[i]]
    if (!key %in% c("--input", "--audit", "--out-dir") || i == length(args)) {
      stop(sprintf("Unexpected or incomplete argument: %s", key), call. = FALSE)
    }
    value <- args[[i + 1]]
    if (key == "--input") result$input <- value
    if (key == "--audit") result$audit <- value
    if (key == "--out-dir") result$out_dir <- value
    i <- i + 2
  }
  result
}

stop_if <- function(condition, message) {
  if (isTRUE(condition)) stop(message, call. = FALSE)
}

read_and_validate_panel <- function(path, audit_path) {
  stop_if(!file.exists(path), sprintf("Panel file not found: %s", path))
  stop_if(!file.exists(audit_path), sprintf("Panel audit not found: %s", audit_path))
  panel <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
  audit <- jsonlite::fromJSON(audit_path, simplifyVector = TRUE)

  required <- c(
    "survey_date", "season", "building_id", "facade_label", "facade_id",
    "method_code", "survey_hours", "mortality_count", "mortality_present",
    "facade_area_m2", "glass_area_m2", "facade_porous_cover_percent",
    "facade_tree_cover_percent", "stories_reflecting_canopy"
  )
  missing <- setdiff(required, names(panel))
  stop_if(length(missing) > 0, paste("Panel missing fields:", paste(missing, collapse = ", ")))
  stop_if(nrow(panel) != 8835, sprintf("Expected 8835 rows, found %d", nrow(panel)))
  stop_if(length(unique(panel$building_id)) != 8, "Expected eight buildings")
  stop_if(length(unique(panel$facade_id)) != 57, "Expected 57 facades")
  stop_if(length(unique(panel$survey_date)) != 155, "Expected 155 survey dates")
  stop_if(anyDuplicated(panel[c("building_id", "facade_label", "survey_date")]) > 0,
          "Duplicate building/facade/date keys in canonical panel")
  stop_if(!isTRUE(audit$source_sha256_pinned), "Canonical panel source hash is not pinned")
  stop_if(any(!panel$method_code %in% c(1, 2)), "METHOD must be 1 or 2")
  stop_if(any(panel$survey_hours != 24 * panel$method_code), "Survey-hour exposure does not match METHOD")
  stop_if(any(!panel$mortality_present %in% c(0, 1)), "mortality_present must be binary")
  stop_if(any(panel$mortality_present != as.integer(panel$mortality_count > 0)),
          "mortality_present is inconsistent with COLLISIONMORTALITY_X")
  stop_if(any(panel$survey_hours <= 0), "Survey exposure must be positive")
  stop_if(any(panel$facade_area_m2 <= 0), "Facade area must be positive")
  stop_if(any(panel$glass_area_m2 < 0 | panel$glass_area_m2 > panel$facade_area_m2),
          "Glass area must be between zero and facade area")
  stop_if(any(panel$facade_porous_cover_percent < 0 | panel$facade_porous_cover_percent > 100),
          "Facade porous cover must lie in [0,100]")
  stop_if(any(panel$facade_tree_cover_percent < 0 | panel$facade_tree_cover_percent > 100),
          "Facade tree cover must lie in [0,100]")
  stop_if(any(panel$stories_reflecting_canopy < 0 | panel$stories_reflecting_canopy > 8),
          "Stories reflecting canopy must lie in [0,8]")
  panel$season <- factor(tolower(panel$season), levels = c("fall", "winter", "spring", "summer"))
  stop_if(any(is.na(panel$season)), "Unknown season label")
  panel$building_id <- factor(panel$building_id)
  panel$facade_label <- factor(panel$facade_label)
  panel$facade_id <- factor(panel$facade_id)
  list(panel = panel, audit = audit)
}

predictor_map <- c(
  facade_area_z = "facade_area_m2",
  glass_area_z = "glass_area_m2",
  facade_porous_cover_z = "facade_porous_cover_percent",
  facade_tree_cover_z = "facade_tree_cover_percent",
  stories_reflecting_canopy_z = "stories_reflecting_canopy"
)

scale_predictors <- function(train, test = NULL) {
  scales <- list()
  for (z_name in names(predictor_map)) {
    raw_name <- predictor_map[[z_name]]
    mu <- mean(train[[raw_name]], na.rm = TRUE)
    sigma <- stats::sd(train[[raw_name]], na.rm = TRUE)
    stop_if(!is.finite(sigma) || sigma <= 0, sprintf("No variation in %s", raw_name))
    train[[z_name]] <- (train[[raw_name]] - mu) / sigma
    if (!is.null(test)) test[[z_name]] <- (test[[raw_name]] - mu) / sigma
    scales[[raw_name]] <- list(mean = mu, sd = sigma)
  }
  list(train = train, test = test, scales = scales)
}

model_fixed_terms <- list(
  full = paste(
    "facade_area_z * glass_area_z + facade_porous_cover_z +",
    "facade_tree_cover_z + stories_reflecting_canopy_z"
  ),
  building_only = "facade_area_z * glass_area_z + stories_reflecting_canopy_z",
  vegetation_only = paste(
    "facade_porous_cover_z + facade_tree_cover_z +",
    "stories_reflecting_canopy_z"
  ),
  null = "1"
)

make_formula <- function(model_name) {
  fixed <- model_fixed_terms[[model_name]]
  as.formula(paste(
    "mortality_present ~", fixed,
    "+ offset(log(survey_hours)) + (1 | facade_id)"
  ))
}

fit_one_model <- function(data, season, model_name) {
  formula <- make_formula(model_name)
  fit <- tryCatch(
    glmmTMB(
      formula = formula,
      data = data,
      family = binomial(link = "logit"),
      control = glmmTMBControl(
        optCtrl = list(iter.max = 10000, eval.max = 10000)
      )
    ),
    error = function(e) e
  )
  if (inherits(fit, "error")) {
    return(list(
      fit = NULL,
      row = data.frame(
        season = season, model = model_name, formula = paste(deparse(formula), collapse = ""),
        converged = FALSE, convergence_code = NA_integer_, pd_hessian = FALSE,
        n = nrow(data), k = NA_real_, logLik = NA_real_, AIC = NA_real_, AICc = NA_real_,
        message = conditionMessage(fit), stringsAsFactors = FALSE
      )
    ))
  }

  ll <- tryCatch(as.numeric(logLik(fit)), error = function(e) NA_real_)
  k <- tryCatch(as.numeric(attr(logLik(fit), "df")), error = function(e) NA_real_)
  n <- tryCatch(as.numeric(nobs(fit)), error = function(e) nrow(data))
  aic <- tryCatch(as.numeric(AIC(fit)), error = function(e) NA_real_)
  aicc <- if (is.finite(aic) && is.finite(k) && n > k + 1) {
    aic + (2 * k * (k + 1)) / (n - k - 1)
  } else {
    NA_real_
  }
  convergence_code <- tryCatch(as.integer(fit$fit$convergence), error = function(e) NA_integer_)
  pd_hessian <- tryCatch(isTRUE(fit$sdr$pdHess), error = function(e) FALSE)
  converged <- identical(convergence_code, 0L) && pd_hessian && is.finite(aicc)
  message <- tryCatch(as.character(fit$fit$message), error = function(e) "")
  list(
    fit = fit,
    row = data.frame(
      season = season, model = model_name, formula = paste(deparse(formula), collapse = ""),
      converged = converged, convergence_code = convergence_code, pd_hessian = pd_hessian,
      n = n, k = k, logLik = ll, AIC = aic, AICc = aicc,
      message = message, stringsAsFactors = FALSE
    )
  )
}

auc_rank <- function(y, probability) {
  if (length(unique(y)) < 2) return(NA_real_)
  positive <- sum(y == 1)
  negative <- sum(y == 0)
  ranks <- rank(probability, ties.method = "average")
  (sum(ranks[y == 1]) - positive * (positive + 1) / 2) / (positive * negative)
}

extract_coefficients <- function(fit, season, model_name) {
  table <- summary(fit)$coefficients$cond
  if (is.null(table) || nrow(table) == 0) return(data.frame())
  result <- data.frame(
    season = season,
    model = model_name,
    term = rownames(table),
    estimate_log_odds_per_sd = table[, "Estimate"],
    standard_error = table[, "Std. Error"],
    z_value = table[, "z value"],
    p_value = table[, "Pr(>|z|)"],
    odds_ratio_per_sd = exp(table[, "Estimate"]),
    odds_ratio_95_low_per_sd = exp(table[, "Estimate"] - 1.96 * table[, "Std. Error"]),
    odds_ratio_95_high_per_sd = exp(table[, "Estimate"] + 1.96 * table[, "Std. Error"]),
    stringsAsFactors = FALSE
  )
  result
}


make_response_curves <- function(fit, season_data, season, model_name, scales) {
  specs <- list(
    facade_area_m2 = list(z = "facade_area_z", raw = "facade_area_m2"),
    glass_area_m2 = list(z = "glass_area_z", raw = "glass_area_m2"),
    facade_porous_cover_percent = list(z = "facade_porous_cover_z", raw = "facade_porous_cover_percent"),
    facade_tree_cover_percent = list(z = "facade_tree_cover_z", raw = "facade_tree_cover_percent"),
    stories_reflecting_canopy = list(z = "stories_reflecting_canopy_z", raw = "stories_reflecting_canopy")
  )
  fixed_terms <- model_fixed_terms[[model_name]]
  output <- list()
  for (predictor in names(specs)) {
    spec <- specs[[predictor]]
    if (!grepl(spec$z, fixed_terms, fixed = TRUE)) next
    facade_values <- unique(season_data[[spec$raw]])
    grid <- seq(
      as.numeric(stats::quantile(facade_values, 0.05, na.rm = TRUE)),
      as.numeric(stats::quantile(facade_values, 0.95, na.rm = TRUE)),
      length.out = 25
    )
    for (hours in c(24, 48)) {
      newdata <- data.frame(
        survey_hours = rep(hours, length(grid)),
        facade_area_z = rep(
          (median(season_data$facade_area_m2) - scales$facade_area_m2$mean) /
            scales$facade_area_m2$sd, length(grid)
        ),
        glass_area_z = rep(
          (median(season_data$glass_area_m2) - scales$glass_area_m2$mean) /
            scales$glass_area_m2$sd, length(grid)
        ),
        facade_porous_cover_z = rep(
          (median(season_data$facade_porous_cover_percent) - scales$facade_porous_cover_percent$mean) /
            scales$facade_porous_cover_percent$sd, length(grid)
        ),
        facade_tree_cover_z = rep(
          (median(season_data$facade_tree_cover_percent) - scales$facade_tree_cover_percent$mean) /
            scales$facade_tree_cover_percent$sd, length(grid)
        ),
        stories_reflecting_canopy_z = rep(
          (median(season_data$stories_reflecting_canopy) - scales$stories_reflecting_canopy$mean) /
            scales$stories_reflecting_canopy$sd, length(grid)
        ),
        building_id = factor(rep(levels(season_data$building_id)[1], length(grid)),
                             levels = levels(season_data$building_id)),
        facade_label = factor(rep(levels(season_data$facade_label)[1], length(grid)),
                              levels = levels(season_data$facade_label)),
        facade_id = factor(rep(levels(season_data$facade_id)[1], length(grid)),
                           levels = levels(season_data$facade_id))
      )
      newdata[[spec$z]] <- (grid - scales[[spec$raw]]$mean) / scales[[spec$raw]]$sd
      prediction <- tryCatch(
        predict(
          fit, newdata = newdata, type = "link", se.fit = TRUE,
          re.form = NA, allow.new.levels = TRUE
        ),
        error = function(e) e
      )
      if (inherits(prediction, "error")) {
        output[[length(output) + 1]] <- data.frame(
          season = season, model = model_name, predictor = predictor,
          predictor_value = grid, survey_hours = hours,
          predicted_probability = NA_real_, lower_95 = NA_real_, upper_95 = NA_real_,
          prediction_error = conditionMessage(prediction),
          stringsAsFactors = FALSE
        )
        next
      }
      eta <- as.numeric(prediction$fit)
      standard_error <- as.numeric(prediction$se.fit)
      output[[length(output) + 1]] <- data.frame(
        season = season, model = model_name, predictor = predictor,
        predictor_value = grid, survey_hours = hours,
        predicted_probability = stats::plogis(eta),
        lower_95 = stats::plogis(eta - 1.96 * standard_error),
        upper_95 = stats::plogis(eta + 1.96 * standard_error),
        prediction_error = "",
        stringsAsFactors = FALSE
      )
    }
  }
  if (!length(output)) return(data.frame())
  do.call(rbind, output)
}

run_dharma_diagnostics <- function(fit, season) {
  tryCatch({
    simulation <- DHARMa::simulateResiduals(fittedModel = fit, n = 250, plot = FALSE)
    uniformity <- DHARMa::testUniformity(simulation, plot = FALSE)
    dispersion <- DHARMa::testDispersion(simulation, plot = FALSE)
    zero_inflation <- DHARMa::testZeroInflation(simulation, plot = FALSE)
    list(
      season = season,
      n_simulations = 250,
      uniformity_p = as.numeric(uniformity$p.value),
      dispersion_p = as.numeric(dispersion$p.value),
      zero_inflation_p = as.numeric(zero_inflation$p.value),
      interpretation = "Diagnostic p-values are screens; inspect simulated residual plots before substantive use."
    )
  }, error = function(e) {
    list(season = season, error = conditionMessage(e))
  })
}

fit_leave_one_building_out <- function(data, seasons) {
  output <- list()
  full_formula <- make_formula("full")
  for (season in seasons) {
    season_data <- data[data$season == season, , drop = FALSE]
    for (held_out in levels(data$building_id)) {
      train_raw <- season_data[season_data$building_id != held_out, , drop = FALSE]
      test_raw <- season_data[season_data$building_id == held_out, , drop = FALSE]
      if (nrow(test_raw) == 0 || length(unique(train_raw$mortality_present)) < 2) {
        output[[length(output) + 1]] <- data.frame(
          season = as.character(season), held_out_building = held_out,
          n_train = nrow(train_raw), n_test = nrow(test_raw),
          n_test_positive = sum(test_raw$mortality_present), converged = FALSE,
          auc = NA_real_, brier = NA_real_, log_loss = NA_real_,
          baseline_brier = NA_real_, baseline_log_loss = NA_real_,
          message = "Insufficient training outcomes or test rows",
          stringsAsFactors = FALSE
        )
        next
      }
      scaled <- scale_predictors(train_raw, test_raw)
      train <- scaled$train
      test <- scaled$test
      train$facade_id <- droplevels(factor(train$facade_id))
      test$facade_id <- factor(
        test$facade_id,
        levels = unique(c(levels(train$facade_id), as.character(test$facade_id)))
      )
      fit <- tryCatch(
        glmmTMB(
          formula = full_formula,
          data = train,
          family = binomial(link = "logit"),
          control = glmmTMBControl(optCtrl = list(iter.max = 10000, eval.max = 10000))
        ),
        error = function(e) e
      )
      if (inherits(fit, "error")) {
        output[[length(output) + 1]] <- data.frame(
          season = as.character(season), held_out_building = held_out,
          n_train = nrow(train), n_test = nrow(test),
          n_test_positive = sum(test$mortality_present), converged = FALSE,
          auc = NA_real_, brier = NA_real_, log_loss = NA_real_,
          baseline_brier = NA_real_, baseline_log_loss = NA_real_,
          message = conditionMessage(fit), stringsAsFactors = FALSE
        )
        next
      }
      code <- tryCatch(as.integer(fit$fit$convergence), error = function(e) NA_integer_)
      pd <- tryCatch(isTRUE(fit$sdr$pdHess), error = function(e) FALSE)
      converged <- identical(code, 0L) && pd
      prediction <- tryCatch(
        as.numeric(predict(fit, newdata = test, type = "response", re.form = NA, allow.new.levels = TRUE)),
        error = function(e) e
      )
      if (inherits(prediction, "error")) {
        output[[length(output) + 1]] <- data.frame(
          season = as.character(season), held_out_building = held_out,
          n_train = nrow(train), n_test = nrow(test),
          n_test_positive = sum(test$mortality_present), converged = FALSE,
          auc = NA_real_, brier = NA_real_, log_loss = NA_real_,
          baseline_brier = NA_real_, baseline_log_loss = NA_real_,
          message = conditionMessage(prediction), stringsAsFactors = FALSE
        )
        next
      }
      y <- as.integer(test$mortality_present)
      probability <- pmin(pmax(prediction, 1e-8), 1 - 1e-8)
      # Fair exposure-aware benchmark: intercept-only binomial model with the
      # same log-hours offset, rather than a constant rate that ignores METHOD.
      baseline_fit <- tryCatch(
        stats::glm(
          mortality_present ~ offset(log(survey_hours)),
          data = train,
          family = stats::binomial(link = "logit")
        ),
        error = function(e) e
      )
      if (inherits(baseline_fit, "error")) {
        baseline_probability <- rep(NA_real_, nrow(test))
        baseline_converged <- FALSE
        baseline_message <- conditionMessage(baseline_fit)
      } else {
        baseline_probability <- tryCatch(
          as.numeric(stats::predict(baseline_fit, newdata = test, type = "response")),
          error = function(e) rep(NA_real_, nrow(test))
        )
        baseline_probability <- pmin(pmax(baseline_probability, 1e-8), 1 - 1e-8)
        baseline_converged <- isTRUE(baseline_fit$converged) && all(is.finite(baseline_probability))
        baseline_message <- if (baseline_converged) "" else "Exposure-only baseline failed to converge or predict"
      }
      model_brier <- mean((probability - y)^2)
      model_log_loss <- mean(-y * log(probability) - (1 - y) * log(1 - probability))
      baseline_brier <- if (baseline_converged) mean((baseline_probability - y)^2) else NA_real_
      baseline_log_loss <- if (baseline_converged) {
        mean(-y * log(baseline_probability) - (1 - y) * log(1 - baseline_probability))
      } else {
        NA_real_
      }
      output[[length(output) + 1]] <- data.frame(
        season = as.character(season), held_out_building = held_out,
        n_train = nrow(train), n_test = nrow(test),
        n_train_positive = sum(train$mortality_present),
        n_test_positive = sum(y), converged = converged,
        auc = auc_rank(y, probability),
        brier = model_brier,
        log_loss = model_log_loss,
        baseline_converged = baseline_converged,
        baseline_brier = baseline_brier,
        baseline_log_loss = baseline_log_loss,
        brier_skill_vs_exposure_baseline = if (is.finite(baseline_brier) && baseline_brier > 0) {
          1 - model_brier / baseline_brier
        } else NA_real_,
        log_loss_skill_vs_exposure_baseline = if (is.finite(baseline_log_loss) && baseline_log_loss > 0) {
          1 - model_log_loss / baseline_log_loss
        } else NA_real_,
        baseline_message = baseline_message,
        message = as.character(fit$fit$message),
        stringsAsFactors = FALSE
      )
    }
  }
  do.call(rbind, output)
}

args <- parse_args(commandArgs(trailingOnly = TRUE))
dir.create(args$out_dir, recursive = TRUE, showWarnings = FALSE)
validated <- read_and_validate_panel(args$input, args$audit)
data <- validated$panel
audit <- validated$audit
seasons <- c("fall", "winter", "spring", "summer")
scaled <- scale_predictors(data)
data <- scaled$train
scales <- scaled$scales

selection_rows <- list()
coefficient_rows <- list()
response_curve_rows <- list()
seasonal_fits <- list()
diagnostics <- list()
for (season in seasons) {
  season_data <- droplevels(data[data$season == season, , drop = FALSE])
  fits <- list()
  for (model_name in names(model_fixed_terms)) {
    result <- fit_one_model(season_data, season, model_name)
    fits[[model_name]] <- result
    selection_rows[[length(selection_rows) + 1]] <- result$row
    if (!is.null(result$fit)) {
      coefficient_rows[[length(coefficient_rows) + 1]] <-
        extract_coefficients(result$fit, season, model_name)
    }
  }
  local_selection <- do.call(rbind, lapply(fits, function(x) x$row))
  valid <- local_selection[local_selection$converged & is.finite(local_selection$AICc), , drop = FALSE]
  if (nrow(valid) == 0) {
    stop(sprintf("No converged AICc model in season %s", season), call. = FALSE)
  }
  valid <- valid[order(valid$AICc), , drop = FALSE]
  best_name <- valid$model[1]
  best_fit <- fits[[best_name]]$fit
  local_selection$delta_AICc <- ifelse(
    is.finite(local_selection$AICc),
    local_selection$AICc - min(valid$AICc),
    NA_real_
  )
  local_selection$plausible_delta_AICc_le_2 <-
    is.finite(local_selection$delta_AICc) & local_selection$delta_AICc <= 2
  for (i in seq_along(selection_rows)) {
    if (selection_rows[[i]]$season[1] == season) {
      selection_rows[[i]]$delta_AICc <- local_selection$delta_AICc[match(selection_rows[[i]]$model[1], local_selection$model)]
      selection_rows[[i]]$plausible_delta_AICc_le_2 <- local_selection$plausible_delta_AICc_le_2[match(selection_rows[[i]]$model[1], local_selection$model)]
    }
  }
  diagnostics[[season]] <- run_dharma_diagnostics(best_fit, season)
  # Match the paper's figure convention: plot every plausible model within
  # delta AICc <= 2 (not only the single best-ranked model).
  plausible_names <- valid$model[valid$AICc - min(valid$AICc) <= 2]
  curve_frames <- lapply(plausible_names, function(model_name) {
    make_response_curves(
      fits[[model_name]]$fit, season_data, season, model_name, scales
    )
  })
  curve_frames <- Filter(function(x) !is.null(x) && nrow(x) > 0, curve_frames)
  season_curves <- if (length(curve_frames)) do.call(rbind, curve_frames) else data.frame()
  if (nrow(season_curves) > 0) {
    response_curve_rows[[length(response_curve_rows) + 1]] <- season_curves
  }
  seasonal_fits[[season]] <- list(
    n = nrow(season_data),
    positive_visits = sum(season_data$mortality_present),
    mortality_events = sum(season_data$mortality_count),
    survey_hours = sum(season_data$survey_hours),
    best_model = best_name,
    plausible_models = valid$model[valid$AICc - min(valid$AICc) <= 2],
    best_model_AICc = valid$AICc[1],
    best_model_convergence = fits[[best_name]]$row$message,
    best_model_coefficients = extract_coefficients(best_fit, season, best_name),
    response_curve_predictors = if (nrow(season_curves) > 0) unique(season_curves$predictor) else character(),
    diagnostics = diagnostics[[season]]
  )
}

selection <- do.call(rbind, selection_rows)
expected_model_df <- c(full = 8L, building_only = 6L, vegetation_only = 5L, null = 2L)
for (row_index in seq_len(nrow(selection))) {
  row <- selection[row_index, ]
  if (isTRUE(row$converged) &&
      as.integer(row$k) != expected_model_df[[row$model]]) {
    stop(sprintf(
      "Model %s has df=%s; published Build:Fac specification expects df=%s",
      row$model, row$k, expected_model_df[[row$model]]
    ), call. = FALSE)
  }
}
selection <- selection[order(selection$season, selection$AICc), , drop = FALSE]
coefficients <- if (length(coefficient_rows)) do.call(rbind, coefficient_rows) else data.frame()
write.csv(selection, file.path(args$out_dir, "ubc_seasonal_model_selection.csv"), row.names = FALSE, na = "")
write.csv(coefficients, file.path(args$out_dir, "ubc_seasonal_coefficients.csv"), row.names = FALSE, na = "")
response_curves <- if (length(response_curve_rows)) do.call(rbind, response_curve_rows) else data.frame()
write.csv(response_curves, file.path(args$out_dir, "ubc_seasonal_response_curves.csv"),
          row.names = FALSE, na = "")

static <- unique(data[c("facade_id", "facade_area_m2", "glass_area_m2",
                        "facade_porous_cover_percent", "facade_tree_cover_percent",
                        "stories_reflecting_canopy")])
static_predictors <- c("facade_area_m2", "glass_area_m2", "facade_porous_cover_percent",
                       "facade_tree_cover_percent", "stories_reflecting_canopy")
correlation_matrix <- stats::cor(static[static_predictors], use = "complete.obs")
write.csv(correlation_matrix, file.path(args$out_dir, "ubc_facade_feature_correlations.csv"))
vif_values <- sapply(static_predictors, function(target) {
  others <- setdiff(static_predictors, target)
  formula <- as.formula(paste(target, "~", paste(others, collapse = " + ")))
  fit <- stats::lm(formula, data = static)
  1 / (1 - summary(fit)$r.squared)
})
write.csv(data.frame(feature = names(vif_values), VIF = as.numeric(vif_values)),
          file.path(args$out_dir, "ubc_facade_feature_vif.csv"), row.names = FALSE)

lobo <- fit_leave_one_building_out(data, seasons)

summarize_lobo <- function(results) {
  season_names <- sort(unique(as.character(results$season)))
  summaries <- lapply(season_names, function(season_name) {
    part <- results[as.character(results$season) == season_name, , drop = FALSE]
    valid <- part[
      part$converged & part$n_test > 0 &
        is.finite(part$brier) & is.finite(part$baseline_brier) &
        is.finite(part$log_loss) & is.finite(part$baseline_log_loss),
      , drop = FALSE
    ]
    if (nrow(valid) == 0) {
      return(data.frame(
        season = season_name, expected_building_folds = nrow(part),
        evaluated_building_folds = 0L, test_visits = 0L,
        test_positive_visits = 0L, oof_brier = NA_real_,
        offset_only_brier = NA_real_, delta_brier = NA_real_,
        oof_log_loss = NA_real_, offset_only_log_loss = NA_real_,
        delta_log_loss = NA_real_, brier_folds_better = 0L,
        log_loss_folds_better = 0L, mean_fold_auc = NA_real_,
        auc_defined_folds = 0L, stringsAsFactors = FALSE
      ))
    }
    total_n <- sum(valid$n_test)
    weighted <- function(column) {
      sum(valid$n_test * valid[[column]]) / total_n
    }
    auc_values <- valid$auc[is.finite(valid$auc)]
    oof_brier <- weighted("brier")
    baseline_brier <- weighted("baseline_brier")
    oof_log_loss <- weighted("log_loss")
    baseline_log_loss <- weighted("baseline_log_loss")
    data.frame(
      season = season_name,
      expected_building_folds = nrow(part),
      evaluated_building_folds = nrow(valid),
      test_visits = total_n,
      test_positive_visits = sum(valid$n_test_positive),
      oof_brier = oof_brier,
      offset_only_brier = baseline_brier,
      delta_brier = oof_brier - baseline_brier,
      oof_log_loss = oof_log_loss,
      offset_only_log_loss = baseline_log_loss,
      delta_log_loss = oof_log_loss - baseline_log_loss,
      brier_folds_better = sum(valid$brier < valid$baseline_brier),
      log_loss_folds_better = sum(valid$log_loss < valid$baseline_log_loss),
      mean_fold_auc = if (length(auc_values)) mean(auc_values) else NA_real_,
      auc_defined_folds = length(auc_values),
      stringsAsFactors = FALSE
    )
  })
  do.call(rbind, summaries)
}

lobo_summary <- summarize_lobo(lobo)
write.csv(lobo, file.path(args$out_dir, "ubc_leave_one_building_out_validation.csv"),
          row.names = FALSE, na = "")
write.csv(lobo_summary, file.path(args$out_dir, "ubc_leave_one_building_out_summary.csv"),
          row.names = FALSE, na = "")

report <- list(
  source = list(
    name = "Zulian et al. 2023 Appendix 1",
    sha256 = audit$source_sha256,
    sha256_pinned = audit$source_sha256_pinned
  ),
  model = list(
    primary_outcome = "mortality_present = 1(COLLISIONMORTALITY_X > 0)",
    family = "binomial",
    link = "logit",
    estimation = "maximum likelihood via glmmTMB",
    seasonal_fits = seasonal_fits,
    candidate_sets = model_fixed_terms,
    random_effects = "(1 | facade_id), matching the published (1 | Build:Fac) grouping",
    offset = "log(survey_hours), with METHOD 1=24h and METHOD 2=48h",
    scaling = "predictors standardized to mean 0 and SD 1 on the full balanced panel",
    model_selection = "AICc; delta AICc <= 2 reported as plausible",
    conditional_response_curves = paste(
      "Fixed-effect predictions from every model within delta AICc <= 2; random effects are excluded.",
      "Other predictors are held at their season-specific medians; both 24-hour and 48-hour exposures are shown.",
      "Confidence intervals are Wald intervals on the link scale; curves are observational predictions, not causal treatment effects."
    ),
    diagnostics = diagnostics,
    lobo_validation = "leave-one-building-out on the full candidate model; population-level predictions exclude held-out random effects",
    lobo_validation_summary = lobo_summary,
    lobo_interpretation = paste(
      "The offset-only binomial model is the predictive control. Positive delta Brier/log-loss means the full GLMM performs worse.",
      "These are internal held-out-building transfer checks, not external-site validation."
    )
  ),
  feature_correlations = correlation_matrix,
  feature_vif = vif_values,
  limitations = c(
    "The response is detected carcass presence, not true bird approach probability or detection-corrected mortality.",
    "This reproduces the UBC 2023 seasonal analysis; it is not a BNBU collision-rate model or calibration.",
    "Only eight buildings and 57 facades from one temperate Pacific campus are represented.",
    "Glass area is not a categorical glass product or spectral reflectance/transmittance measure.",
    "Building-level VEGE_PERC is not the facade-level porous-cover predictor.",
    "Leave-one-building-out is an internal UBC transfer check, not external validation to another campus.",
    "Summer has few positive surveys; coefficients and diagnostics must be interpreted cautiously."
  ),
  paper_benchmarks = list(
    fall = "building-only model most supported; AreaGlass and StorReflVeg positive",
    winter = "building-only and full models most supported; AreaGlass and FacArea positive",
    spring = "building-only and full models most supported; AreaGlass positive",
    summer = "null and building-only models most supported; AreaGlass positive in building-only"
  ),
  run = list(
    panel_rows = nrow(data),
    buildings = length(unique(data$building_id)),
    facades = length(unique(data$facade_id)),
    survey_dates = length(unique(data$survey_date)),
    season_counts = as.list(table(data$season)),
    predictor_scales = scales,
    R_version = R.version.string,
    package_versions = list(
      glmmTMB = as.character(packageVersion("glmmTMB")),
      DHARMa = as.character(packageVersion("DHARMa")),
      jsonlite = as.character(packageVersion("jsonlite"))
    )
  )
)
jsonlite::write_json(
  report,
  path = file.path(args$out_dir, "ubc_seasonal_model_run.json"),
  auto_unbox = TRUE,
  pretty = TRUE,
  na = "null"
)

cat(jsonlite::toJSON(list(
  seasonal_best_models = lapply(seasonal_fits, function(x) x$best_model),
  seasonal_positive_visits = lapply(seasonal_fits, function(x) x$positive_visits),
  lobo_rows = nrow(lobo),
  lobo_summary = lobo_summary,
  output_directory = args$out_dir
), auto_unbox = TRUE, pretty = TRUE))
