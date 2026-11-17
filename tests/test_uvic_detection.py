from __future__ import annotations
import csv, io
from birdglass.uvic_detection import audit_detection_sources

def to_csv(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()

def test_detection_audit_keeps_missing_outcomes_separate_from_no_detection():
    search = [
        {"ID":"a","Season":"Fall","SeasonYear":"SepOct2019","Building":"DTB","Building_Facade":"DTB1","s1":"0","s2":"1","s3":"NA","s4":"NA","s5":"NA"},
        {"ID":"b","Season":"Fall","SeasonYear":"SepOct2019","Building":"DTB","Building_Facade":"DTB1","s1":"0","s2":"NA","s3":"NA","s4":"NA","s5":"NA"},
        {"ID":"c","Season":"Fall","SeasonYear":"SepOct2019","Building":"EOW","Building_Facade":"EOW1","s1":"1","s2":"NA","s3":"NA","s4":"NA","s5":"NA"},
    ]
    schedule = [{"SearchDate":"9/16/19","SeasonYear":"SepOct2019",**{b:"1" for b in ("DTB","EOW","FIA","MSB","MWB","UVC")}}]
    persistence = [
        {"ID":"a","Season":"Fall","SeasonYear":"SepOct2019","BuildingFacade":"DTB1","Building":"DTB","BuildingType":"high","LastPresent":"2","FirstAbsent":"4"},
        {"ID":"b","Season":"Fall","SeasonYear":"SepOct2019","BuildingFacade":"DTB1","Building":"DTB","BuildingType":"high","LastPresent":"3","FirstAbsent":"INF"},
    ]
    audit=audit_detection_sources(to_csv(search),to_csv(schedule),to_csv(persistence))
    assert audit["searcher_efficiency"]["risk_sets"][0]["at_risk"] == 3
    assert audit["searcher_efficiency"]["risk_sets"][0]["detected"] == 1
    assert audit["searcher_efficiency"]["risk_sets"][1]["at_risk"] == 2
    assert audit["searcher_efficiency"]["risk_sets"][1]["missing_outcome_while_at_risk"] == 1
    assert audit["carcass_persistence"]["finite_interval_observations"] == 1
    assert audit["carcass_persistence"]["right_censored_observations"] == 1

def test_detection_audit_flags_observation_after_detection():
    search=[{"ID":"a","Season":"Fall","SeasonYear":"SepOct2019","Building":"DTB","Building_Facade":"DTB1","s1":"1","s2":"0","s3":"NA","s4":"NA","s5":"NA"}]
    schedule=[{"SearchDate":"9/16/19","SeasonYear":"SepOct2019",**{b:"1" for b in ("DTB","EOW","FIA","MSB","MWB","UVC")}}]
    persistence=[{"ID":"a","Season":"Fall","SeasonYear":"SepOct2019","BuildingFacade":"DTB1","Building":"DTB","BuildingType":"high","LastPresent":"1","FirstAbsent":"2"}]
    audit=audit_detection_sources(to_csv(search),to_csv(schedule),to_csv(persistence))
    assert audit["searcher_efficiency"]["observations_after_prior_detection"] == 1

def test_detection_audit_flags_invalid_persistence_interval():
    search=[{"ID":"a","Season":"Fall","SeasonYear":"SepOct2019","Building":"DTB","Building_Facade":"DTB1","s1":"0","s2":"NA","s3":"NA","s4":"NA","s5":"NA"}]
    schedule=[{"SearchDate":"9/16/19","SeasonYear":"SepOct2019",**{b:"1" for b in ("DTB","EOW","FIA","MSB","MWB","UVC")}}]
    persistence=[{"ID":"a","Season":"Fall","SeasonYear":"SepOct2019","BuildingFacade":"DTB1","Building":"DTB","BuildingType":"high","LastPresent":"5","FirstAbsent":"3"}]
    audit=audit_detection_sources(to_csv(search),to_csv(schedule),to_csv(persistence))
    assert audit["carcass_persistence"]["invalid_intervals_last_present_after_first_absent"] == 1
