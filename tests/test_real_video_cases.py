"""Synthetic controls plus optional exact-source checks.

Actual 38-case checks are enforced in the external-data workflow;
the default no-network unit test suite retains all synthetic checks.
"""
import os
from pathlib import Path
import pytest
pytest.importorskip("sklearn")

from birdglass.video_case_benchmark import (
    audit_selected_cases, benchmark, leave_group_out, read_original_csv, summary_stat
)


def synthetic_rows():
    rows = []
    for year in (2019, 2020, 2021):
        for species in ("a", "b", "c"):
            for i in range(5):
                rows.append({
                    "date": f"8/1/{year}", "species": species,
                    "velocity": str(2 + i + (year-2019)),
                    "horizangleP": str(i*5),
                    "time_dec": str(8 + i/4),
                    "collnear": str(i % 2),
                    "type": "Collision" if i % 2 else "Nearmiss",
                })
    return rows


def test_group_holdouts_have_no_future_label_scaling():
    rows = synthetic_rows()
    a = leave_group_out(rows, "species")
    b = leave_group_out(rows, "year")
    assert a["n_groups"] == b["n_groups"] == 3
    for obj in (a, b):
        assert obj["models"]["intercept"]["n_predictions"] == 45
        for rec in obj["models"].values():
            assert 0 <= rec["brier"] <= 1
            assert rec["log_loss"] >= 0
            assert rec["identified_population_probability"] is False


def test_predefined_descriptive_sample_sd():
    assert summary_stat(["", 1, 2, 3])["n"] == 3
    assert summary_stat([1, 2, 3])["mean"] == pytest.approx(2)
    assert summary_stat([1, 2, 3])["sample_sd"] == pytest.approx(1)


def test_unapproved_source_hash_fails(tmp_path):
    path = tmp_path / "fake.csv"
    path.write_text("some synthetic invented data\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        read_original_csv(path)


def test_group_type_must_be_predeclared():
    with pytest.raises(ValueError, match="species/year"):
        leave_group_out(synthetic_rows(), "random_frame")


def test_real_published_source_if_attached():
    file_path = os.getenv("BIRDGLASS_PEERJ_2022_CSV")
    if not file_path:
        pytest.skip("Actual source available in evidence workflow; default tests remain offline")
    audit = benchmark(Path(file_path))
    real = audit["audit"]
    assert real["n_selected_video_events"] == 38
    assert real["n_collision_events"] == 29
    assert real["n_near_misses"] == 9
    assert real["n_three_feature_complete"] == 36
    assert real["n_complete_collision"] == 28
    assert real["n_complete_near_miss"] == 8
    assert real["pooled_speed_mps"]["mean"] == pytest.approx(7.2413321855, rel=1e-9)
    assert real["pooled_angle_offset_deg"]["mean"] == pytest.approx(16.52777778, rel=1e-8)
    assert real["collision_only_speed_mps"]["mean"] != pytest.approx(7.24, abs=.02)
    assert real["immediate_died_or_stunned"] == 5
    assert audit["leave_species_out"]["models"]["speed_angle_time"]["brier"] > (
        audit["leave_species_out"]["models"]["intercept"]["brier"])
