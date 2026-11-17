import csv
import hashlib
from pathlib import Path

from scripts.audit_ubc_sources import (
    FILES,
    audit_carcass_persistence,
    audit_search_efficiency,
    audit_survey_table,
    read_csv,
)


def write_csv(path: Path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_facade_survey_preserves_explicit_zeroes(tmp_path):
    path = tmp_path / "appendix1.csv"
    write_csv(path, ["Building", "Facade", "Date", "Season", "Collision"], [
        {"Building": "A", "Facade": "A1", "Date": "2020-01-01", "Season": "winter", "Collision": "0"},
        {"Building": "A", "Facade": "A1", "Date": "2020-01-02", "Season": "winter", "Collision": "1"},
        {"Building": "B", "Facade": "B1", "Date": "2020-01-01", "Season": "winter", "Collision": "0"},
    ])
    result = audit_survey_table(path)
    assert result["rows"] == 3
    assert result["explicit_zero_rows"] == 2
    assert result["positive_rows"] == 1
    assert result["unique_counts"]["facade"] == 2
    assert result["unique_counts"]["building"] == 2


def test_search_efficiency_uses_sequential_risk_sets(tmp_path):
    path = tmp_path / "Search.Efficiency.csv"
    write_csv(path, ["ID", "s1", "s2", "s3"], [
        {"ID": "a", "s1": "1", "s2": "NA", "s3": "NA"},
        {"ID": "b", "s1": "0", "s2": "1", "s3": "NA"},
        {"ID": "c", "s1": "0", "s2": "0", "s3": "1"},
        {"ID": "d", "s1": "0", "s2": "0", "s3": "0"},
    ])
    result = audit_search_efficiency(path)
    hazards = result["conditional_detection_by_search"]
    assert hazards[0]["at_risk_trials_with_observed_result"] == 4
    assert hazards[0]["detections_on_this_search"] == 1
    assert hazards[1]["at_risk_trials_with_observed_result"] == 3
    assert hazards[1]["detections_on_this_search"] == 1
    assert hazards[2]["at_risk_trials_with_observed_result"] == 2
    assert hazards[2]["detections_on_this_search"] == 1


def test_persistence_requires_interval_censoring_fields(tmp_path):
    path = tmp_path / "Carcass.Persistence.csv"
    write_csv(path, ["ID", "LastPresent", "FirstAbsent"], [
        {"ID": "a", "LastPresent": "2.0", "FirstAbsent": "3.0"},
        {"ID": "b", "LastPresent": "4.0", "FirstAbsent": "NA"},
    ])
    result = audit_carcass_persistence(path)
    assert result["status"] == "interval_censoring_fields_detected"
    assert result["last_present_column"] == "LastPresent"
    assert result["first_absent_column"] == "FirstAbsent"
    assert result["interval_censored_trials"] == 1
    assert result["right_censored_trials"] == 1


def test_unknown_response_is_not_silently_zero(tmp_path):
    path = tmp_path / "appendix1.csv"
    write_csv(path, ["Building", "Facade", "Date", "Collision"], [
        {"Building": "A", "Facade": "A1", "Date": "2020-01-01", "Collision": "NA"},
        {"Building": "A", "Facade": "A1", "Date": "2020-01-02", "Collision": "0"},
    ])
    result = audit_survey_table(path)
    assert result["explicit_zero_rows"] == 1
    assert result["unknown_response_rows"] == 1


def test_csv_reader_rejects_duplicate_headers(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("A,A\n1,2\n", encoding="utf-8")
    try:
        read_csv(path)
    except ValueError as error:
        assert "Duplicate" in str(error)
    else:
        raise AssertionError("Duplicate headers should fail")


def test_public_search_efficiency_file_matches_dryad_md5():
    path = Path(__file__).parents[1] / "data" / "raw" / "ubc" / "Search.Efficiency.csv"
    assert path.exists()
    assert FILES["Search.Efficiency.csv"] == ("f9e7a8816ef52eb9d3523f0f14b40d6b", 1766)
    assert hashlib.md5(path.read_bytes()).hexdigest() == "f9e7a8816ef52eb9d3523f0f14b40d6b"
    result = audit_search_efficiency(path)
    assert result["rows"] == 29
    assert result["conditional_detection_by_search"][0]["detections_on_this_search"] == 16
    assert result["conditional_detection_by_search"][1]["at_risk_trials_with_observed_result"] == 13

def test_verified_search_efficiency_season_breakdown():
    path = Path(__file__).parents[1] / "data" / "raw" / "ubc" / "Search.Efficiency.csv"
    result = audit_search_efficiency(path)
    seasons = result["first_search_by_season"]
    assert seasons["fall"]["first_search_detections"] == 0
    assert seasons["fall"]["trials"] == 2
    assert seasons["spring"]["first_search_detections"] == 2
    assert seasons["summer"]["first_search_detections"] == 3
    assert seasons["winter"]["first_search_detections"] == 11
