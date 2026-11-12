#!/usr/bin/env python3
"""Inspect publicly licensed PeerJ coded window-event data from CURRENT PMC Cloud.

The former PMC FTP/legacy article-bin distribution was removed in Aug 2026.
Use the NLM's anonymous, world-readable pmc-oa-opendata S3 API instead.
No accounts, paid service, or tokens are needed.

Scientific restriction: selected collision/near-miss video cases do not
identify the rate among *all* approaching birds.
"""
import csv
import hashlib
import io
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone

BASE="https://pmc-oa-opendata.s3.amazonaws.com"
PMCID="PMC9784330"
DOI="10.7717/peerj.14604"
OUT=Path("results/external/samuels_2022")
OUT.mkdir(parents=True,exist_ok=True)
audit={
    "paper_doi":DOI,
    "supplement_doi":DOI+"/supp-4",
    "pmcid":PMCID,
    "license_note":"Verify per-article metadata; original paper states CC BY 4.0",
    "retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
    "distribution":"NLM PMC Cloud Service post-August-2026",
    "data_scope":"CASE_SELECTED_COLLISION_AND_NEAR_MISS_VIDEOS",
    "unconditional_collision_probability_identified":False,
    "publication_reports":{"collisions":29,"near_misses":9,
                           "other_flybys_excluded_at_least":9},
    "status":"unavailable",
    "attempts":[]
}

def get(url,max_bytes=2_000_000):
    req=urllib.request.Request(url,headers={
        "User-Agent":"birdglass-research-source-verification/1.1",
        "Accept":"application/xml,application/json,text/csv,*/*"})
    with urllib.request.urlopen(req,timeout=18) as r:
        blob=r.read(max_bytes+1)
    if len(blob)>max_bytes:
        raise ValueError("Unexpectedly large source object")
    if b"<html" in blob[:400].lower():
        raise ValueError("HTML instead of source bytes")
    return blob

try:
    # Listing a SINGLE article's available object versions, not a bulk scrape.
    params=urllib.parse.urlencode({
        "list-type":"2","prefix":PMCID+".","delimiter":"/"})
    listing=f"{BASE}/?{params}"
    root=ET.fromstring(get(listing,max_bytes=131072))
    def suffix(tag):
        return tag.split('}')[-1]
    prefixes=[
        (child.text or "").rstrip("/")
        for parent in root.iter() if suffix(parent.tag)=="CommonPrefixes"
        for child in parent if suffix(child.tag)=="Prefix"
    ]
    # ListObjectsV2 namespace is handled by stripping XML tag namespaces.
    prefixes=sorted({p for p in prefixes if p.startswith(PMCID+".")})
    if not prefixes:
        raise ValueError("No article version in official PMC S3 list")
    audit["discovered_article_versions"]=prefixes
    for version in prefixes:
        try:
            metadata_url=f"{BASE}/metadata/{version}.json"
            meta=json.loads(get(metadata_url,250000))
            if str(meta.get("doi","")).lower()!=DOI:
                raise ValueError("PMCID metadata DOI mismatch")
            license_code=str(meta.get("license_code",""))
            if "by" not in license_code.lower():
                raise ValueError("A CC BY redistribution license was not confirmed")
            if str(meta.get("is_retracted","")).lower() in {"yes","true","1"}:
                raise ValueError("Article marked retracted")
            media=meta.get("media_urls",[])
            if not isinstance(media,list):
                raise ValueError("Invalid media_urls metadata")
            urls=[m if isinstance(m,str) else m.get("url","")
                  for m in media if isinstance(m,(str,dict))]
            selected=[u for u in urls
                     if "peerj-10-14604-s004.csv" in u.lower()
                     or "s004.csv" in urllib.parse.urlparse(u).path.lower()]
            if not selected:
                # Permit only an explicitly documented exact object key,
                # never guess a different supplement or silently repurpose it.
                selected=[f"{BASE}/{version}/peerj-10-14604-s004.csv"]
            for url in selected:
                try:
                    blob=get(url,65536)
                    raw=blob.decode("utf-8-sig")
                    rdr=csv.DictReader(io.StringIO(raw))
                    rows=list(rdr)
                    columns=rdr.fieldnames or []
                    if (len(rows)<30 or len(rows)>60 or len(columns)<3
                        or len(set(columns))!=len(columns)
                        or any(None in r for r in rows)):
                        raise ValueError("Unexpected event-table shape, manual review needed")
                    (OUT/"peerj_14604_supp4_coded_events.csv").write_bytes(blob)
                    audit.update({
                        "status":"downloaded_schema_requires_semantic_review",
                        "source_url":url,
                        "article_version":version,
                        "metadata_url":metadata_url,
                        "license_code_from_metadata":license_code,
                        "sha256":hashlib.sha256(blob).hexdigest(),
                        "n_data_rows":len(rows),
                        "column_names":columns,
                        "missing_cell_count_by_column":{
                            k:sum(not str(r.get(k,"")).strip() for r in rows)
                            for k in columns
                        },
                        "raw_rows_have_all_approaches_denominator":False,
                        "semantic_coding_validated":False,
                    })
                    print("FOUND CURRENT PMC S3:",url)
                    print("COLUMNS:",columns)
                    print("ROWS:",len(rows),"SHA256:",audit["sha256"])
                    break
                except Exception as exc:
                    audit["attempts"].append({"url":url,
                        "error":type(exc).__name__+": "+str(exc)[:160]})
            if audit["status"].startswith("downloaded"):
                break
        except Exception as exc:
            audit["attempts"].append({"version":version,
                "error":type(exc).__name__+": "+str(exc)[:160]})
except Exception as exc:
    audit["attempts"].append({"distribution":"PMC_S3",
        "error":type(exc).__name__+": "+str(exc)[:180]})

if audit["status"]=="unavailable":
    print("SOURCE UNAVAILABLE: the program has NOT fabricated original rows")
for a in audit["attempts"]:
    print("attempt:",a)
(OUT/"source_audit.json").write_text(json.dumps(
    audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
