import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from summarize_ubc_lobo_uncertainty import (
    SEASONS, percentile, read_folds, summarize, weighted_delta,
)


def rows():
    return [
        dict(
            season=season, held_out_building=building, n_test="100",
            n_test_positive="2", converged="TRUE", baseline_converged="TRUE",
            brier="0.03", baseline_brier="0.02",
            log_loss="0.15", baseline_log_loss="0.10",
        )
        for building in "ABCDEFGH" for season in SEASONS
    ]


def write(path, records):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def test_cluster_bootstrap_is_paired_and_reproducible(tmp_path):
    source = tmp_path / "folds.csv"
    write(source, rows())
    parsed = read_folds(source)
    result = summarize(parsed, n_boot=200, seed=2)
    assert len(result) == 10
    assert all(row["n_held_out_buildings"] == 8 for row in result)
    for row in result:
        expected = 0.01 if row["metric"] == "brier" else 0.05
        assert row["delta_model_minus_offset"] == pytest.approx(expected)
        assert row["building_bootstrap_ci_low"] == pytest.approx(expected)
        assert row["building_bootstrap_ci_high"] == pytest.approx(expected)
    assert result == summarize(parsed, n_boot=200, seed=2)


def test_nested_model_bootstrap_compares_both_baselines(tmp_path):
    records = rows()
    for row in records:
        row["fixed_full_converged"] = "TRUE"
        row["fixed_full_brier"] = "0.04"
        row["fixed_full_log_loss"] = "0.17"
    source = tmp_path / "nested.csv"
    write(source, records)
    parsed = read_folds(source)
    result = summarize(parsed, n_boot=200, seed=3)
    assert len(result) == 20
    full_brier = next(
        row for row in result
        if row["stratum"] == "overall"
        and row["comparison"] == "fixed_full_glmm"
        and row["metric"] == "brier"
    )
    assert full_brier["delta_model_minus_fixed_full"] == pytest.approx(-0.01)
    assert full_brier["building_bootstrap_ci_low"] == pytest.approx(-0.01)
    assert full_brier["building_bootstrap_ci_high"] == pytest.approx(-0.01)
    baseline_brier = next(
        row for row in result
        if row["stratum"] == "overall"
        and row["comparison"] == "exposure_only"
        and row["metric"] == "brier"
    )
    assert baseline_brier["delta_model_minus_offset"] == pytest.approx(0.01)


def test_building_multiplicity_weights_whole_cluster():
    values = []
    for building in "AB":
        for season in SEASONS:
            values.append(dict(
                building=building, season=season, n_test=100,
                brier=0.12 if building == "A" else 0.03,
                baseline_brier=0.02, log_loss=0.2, baseline_log_loss=0.1,
            ))
    value = weighted_delta(values, "brier", "fall", {"A": 2, "B": 1})
    assert value == pytest.approx((2 * 0.10 + 0.01) / 3)


@pytest.mark.parametrize("corruption", ["missing", "duplicate", "nan", "failed", "bad_positive"])
def test_invalid_fold_panel_fails_closed(tmp_path, corruption):
    records = rows()
    if corruption == "missing":
        records.pop()
    elif corruption == "duplicate":
        records[-1] = dict(records[0])
    elif corruption == "nan":
        records[0]["brier"] = "nan"
    elif corruption == "failed":
        records[0]["converged"] = "False"
    else:
        records[0]["n_test_positive"] = "101"
    source = tmp_path / "bad.csv"
    write(source, records)
    with pytest.raises(ValueError):
        read_folds(source)


def test_fixed_full_comparator_fails_closed_when_not_converged(tmp_path):
    records = rows()
    for row in records:
        row["fixed_full_converged"] = "FALSE"
        row["fixed_full_brier"] = "0.04"
        row["fixed_full_log_loss"] = "0.17"
    source = tmp_path / "bad_full.csv"
    write(source, records)
    with pytest.raises(ValueError, match="fixed-full"):
        read_folds(source)


def test_percentile_interpolation():
    assert percentile([0.0, 1.0, 2.0], 0.25) == 0.5
