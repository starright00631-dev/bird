import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_real_metadata import build_report

def test_report_recomputes_real_source_counts_without_network():
    result=build_report()
    assert result["n_metadata_rows"]==59
    assert result["n_duplicate_recording_rows"]==18
    assert sum(result["fold_trial_counts"].values())==59
    assert not result["cross_date_biological_identity_certified"]
    assert not result["raw_3d_tracks_available_in_metadata"]
