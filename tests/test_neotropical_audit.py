import pytest

from scripts.audit_neotropical_sampling import audit_rows


def row(identifier, country, method, species, latitude="22.0", longitude="113.0"):
    return {
        "General.ID": str(identifier),
        "Country": country,
        "Latitude": latitude,
        "Longitude": longitude,
        "Data.collection.method": method,
        "Pane.type": "Reflective",
        "Deterrent": "None",
        "Survivorship": "Dead",
        "Month": "October",
        "Date.accuracy": "Exact",
        "Age": "Unknown",
        "Sex": "Unknown",
        "Species": species,
        "Year": "2020",
    }


def test_audit_keeps_country_holdouts_disjoint_and_event_only():
    rows = [
        row(1, "Brazil", "Systematic", "Species alpha"),
        row(2, "Brazil", "By chance", "Species beta"),
        row(3, "China", "Systematic", "Species alpha", "22.1", "113.1"),
    ]
    result = audit_rows(rows)
    assert result["records"] == 3
    assert result["unique_species"] == 2
    assert len(result["country_holdout_folds"]) == 2
    assert all(not fold["country_overlap"] for fold in result["country_holdout_folds"])
    assert "P(collision | bird approach)" in result["not_estimable"]
    assert result["estimable_target"].startswith("composition of reported")


def test_audit_rejects_duplicate_event_ids():
    rows = [
        row(1, "Brazil", "Systematic", "Species alpha"),
        row(1, "Brazil", "Systematic", "Species beta"),
    ]
    with pytest.raises(ValueError, match="Duplicate"):
        audit_rows(rows)


def test_audit_reports_method_country_heterogeneity():
    rows = [
        row(1, "Brazil", "Gov. Agency", "Species alpha"),
        row(2, "Brazil", "Gov. Agency", "Species beta"),
        row(3, "Mexico", "Systematic", "Species alpha", "20.0", "-100.0"),
    ]
    result = audit_rows(rows)
    assert result["collection_method_by_country"]["Brazil"]["Gov. Agency"] == 2
    assert result["collection_method_by_country"]["Mexico"]["Systematic"] == 1
