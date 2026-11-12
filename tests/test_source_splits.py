import csv
from pathlib import Path
import pytest
from birdglass.source_splits import (read_3dpop_metadata,audit_metadata,
                                     component_fold_assignment)

SOURCE=Path(__file__).resolve().parents[1]/"data/external/3dpop_public_metadata.csv"

def test_real_published_registry_counts():
    rows=read_3dpop_metadata(SOURCE.read_text())
    audit=audit_metadata(rows)
    assert audit["n_metadata_rows"]==59
    assert audit["n_subject_session_labels"]==57
    assert audit["n_subject_labels_in_multiple_rows"]==54
    assert audit["n_duplicate_recording_rows"]==18
    assert audit["n_independent_source_groups"]==7
    assert audit["group_sizes_sorted"]==[11,11,11,11,8,5,2]
    assert not audit["cross_date_biological_identity_certified"]
    assert not audit["raw_3d_tracks_available_in_metadata"]

def test_five_folds_do_not_share_any_recording_or_known_subject_label():
    rows=read_3dpop_metadata(SOURCE.read_text())
    folds=component_fold_assignment(rows,5)
    assert set(folds)=={r["sequence"] for r in rows}
    assert set(folds.values())==set(range(5))
    assert sum(1 for r in rows if folds[r["sequence"]]==0)>0
    for a in rows:
      for b in rows:
        if folds[a["sequence"]]!=folds[b["sequence"]]:
          assert not set(a["subjects"]).intersection(b["subjects"])
          assert (a["date"],a["trial"],a["video"])!=(
              b["date"],b["trial"],b["video"])

def test_shared_video_must_cohabit_even_if_subject_labels_differ():
    data=("Sequence,ViconTrial,SonyVideoName,IndividualNum,Date,Subjects\n"
          "1,t1,vid,1,01012022,one\n"
          "2,t1,vid,1,01012022,two\n"
          "3,t2,other,1,02012022,three\n")
    rows=read_3dpop_metadata(data)
    folds=component_fold_assignment(rows,2)
    assert folds["1"]==folds["2"]

def test_duplicate_trial_sequence_and_inconsistent_counts_fail():
    data=SOURCE.read_text()
    lines=data.splitlines()
    with pytest.raises(ValueError):
       read_3dpop_metadata("\n".join(lines[:2]+[lines[1]])+"\n")
    bad=lines[1].split(",")
    bad[3]="10"
    with pytest.raises(ValueError):
       read_3dpop_metadata(lines[0]+"\n"+",".join(bad))

def test_too_many_folds_abstains():
    rows=read_3dpop_metadata(SOURCE.read_text())
    with pytest.raises(ValueError):
       component_fold_assignment(rows,8)
