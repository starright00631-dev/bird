#!/usr/bin/env python3
"""Fetch and independently audit the PeerJ 2022 coded-event supplement.

Only public CC BY-4.0 research data. This optional acquisition is not used
for estimating unconditional bird-window collision probability: the study
sampled selected collisions/near misses rather than all approaches.

Source: Brendon Samuels et al., PeerJ 10:e14604 (2022),
doi:10.7717/peerj.14604, supplementary data 4.
"""
import csv
import hashlib
import io
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen

OUT = Path("results/external/samuels_2022")
OUT.mkdir(parents=True, exist_ok=True)
URLS = (
    "https://pmc.ncbi.nlm.nih.gov/articles/instance/9784330/bin/peerj-10-14604-s004.csv",
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC9784330/bin/peerj-10-14604-s004.csv",
    "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9784330/bin/peerj-10-14604-s004.csv",
    "https://peerj.com/articles/14604/supp-4/",
)
audit = {
    "paper_doi": "10.7717/peerj.14604",
    "supplement_doi": "10.7717/peerj.14604/supp-4",
    "license": "CC BY 4.0; attribution required",
    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    "data_scope": "SELECTED_VIDEO_COLLISION_AND_NEAR_MISS_EVENTS",
    "unconditional_collision_probability_identified": False,
    "publication_reports": {"collisions":29, "near_misses":9,
                             "other_flybys_excluded_at_least":9},
    "status": "unavailable",
    "attempts": []
}
for url in URLS:
    try:
        req = Request(url, headers={
            "User-Agent":"Mozilla/5.0 (compatible; academic-reproducibility/1.0)",
            "Accept":"text/csv,text/plain,application/octet-stream,*/*"})
        with urlopen(req,timeout=16) as response:
            blob = response.read(65536)
            content_type = response.headers.get("Content-Type","")
        if len(blob)>32768:
            raise ValueError("Oversize data; manual inspection required")
        if b"<html" in blob[:400].lower() or "html" in content_type.lower():
            raise ValueError("HTML or anti-bot response, not coded CSV")
        txt = blob.decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(txt)))
        cols = next(csv.reader(io.StringIO(txt)),[])
        if len(rows) < 30 or len(rows)>60 or len(cols)<3:
            raise ValueError(f"Unexpected source schema: nrows={len(rows)},ncols={len(cols)}")
        if len(set(cols))!=len(cols):
            raise ValueError("Duplicate column names")
        if any(None in row for row in rows):
            raise ValueError("Broken CSV row length")
        target=OUT/"peerj_14604_supp4_coded_events.csv"
        target.write_bytes(blob)
        audit.update({
            "status":"downloaded_schema_requires_semantic_review",
            "source_url":url,
            "sha256":hashlib.sha256(blob).hexdigest(),
            "n_data_rows":len(rows),
            "column_names":cols,
            "missing_cell_count_by_column":{
                k:sum(not str(row.get(k,"")).strip()
                      for row in rows) for k in cols
            },
            "raw_rows_have_independent_approach_denominator":False,
            "semantic_coding_validated":False
        })
        print("FOUND:",url)
        print("COLUMNS:",cols)
        print("ROWS:",len(rows),"SHA256:",audit["sha256"])
        break
    except Exception as err:
        audit["attempts"].append({"url":url,
                "error":type(err).__name__+": "+str(err)[:160]})
if audit["status"] == "unavailable":
    print("SOURCE UNAVAILABLE: no data table was fabricated.")
for attempt in audit["attempts"]:
    print("attempt:",attempt["url"],attempt["error"])
(OUT/"source_audit.json").write_text(
    json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
