"""Paired building-clustered uncertainty for UBC held-out-building scores."""
import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path

SEASONS = ("fall", "winter", "spring", "summer")
METRICS = ("brier", "log_loss")
COMPARATORS = {
    "exposure_only": {"brier": "baseline_brier", "log_loss": "baseline_log_loss"},
    "fixed_full_glmm": {"brier": "fixed_full_brier", "log_loss": "fixed_full_log_loss"},
}


def read_folds(path, expected_buildings=8):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        raw = list(reader)
    if len(raw) != len(SEASONS) * expected_buildings:
        raise ValueError("Expected exactly four seasons and one fold per held-out building")
    has_fixed_full = {"fixed_full_brier", "fixed_full_log_loss", "fixed_full_converged"} <= fields
    partial_fixed = bool(fields & {"fixed_full_brier", "fixed_full_log_loss", "fixed_full_converged"})
    if partial_fixed and not has_fixed_full:
        raise ValueError("Incomplete fixed-full comparator columns")
    rows, keys, buildings = [], set(), set()
    for source in raw:
        try:
            season = source["season"].strip().lower()
            building = source["held_out_building"].strip()
            n_test = int(source["n_test"])
            n_positive = int(source["n_test_positive"])
            scores = {
                name: float(source[name])
                for name in ("brier", "baseline_brier", "log_loss", "baseline_log_loss")
            }
            if has_fixed_full:
                scores["fixed_full_brier"] = float(source["fixed_full_brier"])
                scores["fixed_full_log_loss"] = float(source["fixed_full_log_loss"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Malformed UBC held-out-fold record") from exc
        if (
            season not in SEASONS or not building or (season, building) in keys
            or n_test <= 0 or not 0 <= n_positive <= n_test
        ):
            raise ValueError("Invalid/duplicate fold key or survey count")
        if str(source.get("converged", "")).lower() != "true":
            raise ValueError("Non-converged model fold")
        if str(source.get("baseline_converged", "")).lower() != "true":
            raise ValueError("Non-converged exposure-only baseline fold")
        if has_fixed_full and str(source.get("fixed_full_converged", "")).lower() != "true":
            raise ValueError("Non-converged fixed-full comparator fold")
        if not all(math.isfinite(value) for value in scores.values()):
            raise ValueError("Non-finite validation score")
        if any(not 0 <= scores[name] <= 1 for name in ("brier", "baseline_brier")):
            raise ValueError("Brier scores must be in [0, 1]")
        if has_fixed_full and not 0 <= scores["fixed_full_brier"] <= 1:
            raise ValueError("Fixed-full Brier score must be in [0, 1]")
        if any(scores[name] < 0 for name in ("log_loss", "baseline_log_loss")):
            raise ValueError("Log loss must be nonnegative")
        if has_fixed_full and scores["fixed_full_log_loss"] < 0:
            raise ValueError("Fixed-full log loss must be nonnegative")
        keys.add((season, building))
        buildings.add(building)
        rows.append(dict(
            season=season, building=building, n_test=n_test, n_positive=n_positive,
            has_fixed_full=has_fixed_full, **scores
        ))
    if len(buildings) != expected_buildings or any(
        (season, building) not in keys for season in SEASONS for building in buildings
    ):
        raise ValueError("All held-out buildings must appear exactly once in each season")
    return rows


def weighted_delta(rows, metric, season=None, multiplicities=None, comparator="exposure_only"):
    if metric not in METRICS:
        raise ValueError("Unknown metric")
    if comparator not in COMPARATORS:
        raise ValueError("Unknown comparator")
    if comparator == "fixed_full_glmm" and not all(row.get("has_fixed_full") for row in rows):
        raise ValueError("Fixed-full comparator is unavailable")
    comparator_column = COMPARATORS[comparator][metric]
    counts = multiplicities if multiplicities is not None else {
        row["building"]: 1 for row in rows
    }
    total, visits = 0.0, 0
    for row in rows:
        if season is not None and row["season"] != season:
            continue
        weight = row["n_test"] * counts.get(row["building"], 0)
        total += weight * (row[metric] - row[comparator_column])
        visits += weight
    if not visits:
        raise ValueError("Empty evaluation stratum")
    return total / visits


def percentile(sorted_samples, q):
    if not sorted_samples or not 0 <= q <= 1:
        raise ValueError("Invalid percentile input")
    position = (len(sorted_samples) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return sorted_samples[lo] + (position - lo) * (sorted_samples[hi] - sorted_samples[lo])


def summarize(rows, n_boot=5000, seed=20261117):
    if n_boot < 200:
        raise ValueError("At least 200 cluster resamples are required")
    buildings = sorted({row["building"] for row in rows})
    comparators = ["exposure_only"]
    if all(row.get("has_fixed_full") for row in rows):
        comparators.append("fixed_full_glmm")
    rng = random.Random(seed)
    strata = ("overall",) + SEASONS
    samples = {
        (season, comparator, metric): []
        for season in strata for comparator in comparators for metric in METRICS
    }
    for _ in range(n_boot):
        multiplicities = defaultdict(int)
        for _ in buildings:
            multiplicities[rng.choice(buildings)] += 1
        for season in strata:
            season_filter = None if season == "overall" else season
            for comparator in comparators:
                for metric in METRICS:
                    samples[(season, comparator, metric)].append(
                        weighted_delta(rows, metric, season_filter, multiplicities, comparator)
                    )
    output = []
    for season in strata:
        selected = rows if season == "overall" else [
            row for row in rows if row["season"] == season
        ]
        for comparator in comparators:
            for metric in METRICS:
                ordered = sorted(samples[(season, comparator, metric)])
                point = weighted_delta(
                    rows, metric, None if season == "overall" else season, None, comparator
                )
                result = {
                    "stratum": season,
                    "comparison": comparator,
                    "metric": metric,
                    "n_test_visits": sum(row["n_test"] for row in selected),
                    "n_positive_visits": sum(row["n_positive"] for row in selected),
                    "n_held_out_buildings": len(buildings),
                    "delta_model_minus_comparator": point,
                    "building_bootstrap_ci_low": percentile(ordered, 0.025),
                    "building_bootstrap_ci_high": percentile(ordered, 0.975),
                    "n_cluster_resamples": n_boot,
                    "seed": seed,
                }
                if comparator == "exposure_only":
                    result["delta_model_minus_offset"] = point
                else:
                    result["delta_model_minus_fixed_full"] = point
                output.append(result)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="results/ubc/ubc_leave_one_building_out_validation.csv")
    parser.add_argument("--output", default="results/ubc/ubc_lobo_cluster_uncertainty.json")
    parser.add_argument("--resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261117)
    args = parser.parse_args()
    rows = read_folds(args.input)
    results = summarize(rows, n_boot=args.resamples, seed=args.seed)
    comparators = ["exposure-only binomial GLM"]
    if any(row.get("has_fixed_full") for row in rows):
        comparators.append("fixed full GLMM on identical held-out folds")
    report = {
        "source": "Zulian 2023 Appendix 1; SHA pinned in upstream model audit",
        "bootstrap_unit": "building; all four seasonal folds resampled together",
        "metric_definition": "visit-weighted out-of-fold selected-model score minus comparator; negative favors selected model",
        "comparators": comparators,
        "interval": "paired building-cluster percentile bootstrap (descriptive, only eight buildings)",
        "caveat": "Not a confidence interval for transfer to independent campuses, and not uncertainty in intervention efficacy or BNBU collision risk.",
        "results": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
