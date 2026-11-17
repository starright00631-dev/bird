"""Paired building-clustered uncertainty for UBC held-out-building scores."""
import argparse, csv, json, math, random
from collections import defaultdict
from pathlib import Path

SEASONS=("fall","winter","spring","summer")
METRICS=("brier","log_loss")
def read_folds(path, expected_buildings=8):
    with Path(path).open(newline="",encoding="utf-8") as f: raw=list(csv.DictReader(f))
    if len(raw)!=4*expected_buildings: raise ValueError("Expected 4 seasons x 8 building folds")
    rows=[]; keys=set(); buildings=set()
    for x in raw:
        try:
            s=x["season"].strip().lower(); b=x["held_out_building"].strip()
            n=int(x["n_test"]); pos=int(x["n_test_positive"])
            scores={k:float(x[k]) for k in ("brier","baseline_brier","log_loss","baseline_log_loss")}
        except (KeyError,TypeError,ValueError) as e: raise ValueError("Malformed fold") from e
        if s not in SEASONS or not b or (s,b) in keys or n<=0 or not 0<=pos<=n: raise ValueError("Invalid fold key/count")
        if x.get("converged","").lower()!="true" or x.get("baseline_converged","").lower()!="true": raise ValueError("Non-converged fold")
        if not all(math.isfinite(v) for v in scores.values()): raise ValueError("Non-finite score")
        if any(not 0<=scores[k]<=1 for k in ("brier","baseline_brier")) or any(scores[k]<0 for k in ("log_loss","baseline_log_loss")): raise ValueError("Invalid score range")
        keys.add((s,b)); buildings.add(b); rows.append(dict(season=s,building=b,n_test=n,n_positive=pos,**scores))
    if len(buildings)!=expected_buildings or any((s,b) not in keys for s in SEASONS for b in buildings): raise ValueError("Incomplete building-season grid")
    return rows

def weighted_delta(rows,metric,season=None,multiplicities=None):
    if metric not in METRICS: raise ValueError("Unknown metric")
    mult=multiplicities or {r["building"]:1 for r in rows}; total=visits=0.0
    for r in rows:
        if season is not None and r["season"]!=season: continue
        w=r["n_test"]*mult.get(r["building"],0); total+=w*(r[metric]-r["baseline_"+metric]); visits+=w
    if not visits: raise ValueError("Empty stratum")
    return total/visits

def percentile(values,q):
    if not values or not 0<=q<=1: raise ValueError("Invalid percentile")
    p=(len(values)-1)*q; lo=math.floor(p); hi=math.ceil(p)
    return values[lo]+(p-lo)*(values[hi]-values[lo])

def summarize(rows,n_boot=5000,seed=20261117):
    if n_boot<200: raise ValueError("At least 200 resamples required")
    buildings=sorted({r["building"] for r in rows}); rng=random.Random(seed)
    strata=("overall",)+SEASONS; draws={(s,m):[] for s in strata for m in METRICS}
    for _ in range(n_boot):
        counts=defaultdict(int)
        for _ in buildings: counts[rng.choice(buildings)]+=1
        for s in strata:
            for m in METRICS: draws[s,m].append(weighted_delta(rows,m,None if s=="overall" else s,counts))
    out=[]
    for s in strata:
        selected=rows if s=="overall" else [r for r in rows if r["season"]==s]
        for m in METRICS:
            z=sorted(draws[s,m])
            out.append(dict(stratum=s,metric=m,n_test_visits=sum(r["n_test"] for r in selected),n_positive_visits=sum(r["n_positive"] for r in selected),n_held_out_buildings=len(buildings),delta_model_minus_offset=weighted_delta(rows,m,None if s=="overall" else s),building_bootstrap_ci_low=percentile(z,.025),building_bootstrap_ci_high=percentile(z,.975),n_cluster_resamples=n_boot,seed=seed))
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument("--input",default="results/ubc/ubc_leave_one_building_out_validation.csv"); p.add_argument("--output",default="results/ubc/ubc_lobo_cluster_uncertainty.json"); p.add_argument("--resamples",type=int,default=5000); p.add_argument("--seed",type=int,default=20261117); a=p.parse_args()
    rows=read_folds(a.input); result=summarize(rows,a.resamples,a.seed)
    report=dict(source="Zulian 2023 Appendix 1; SHA pinned in upstream audit",bootstrap_unit="building; all four seasonal folds resampled together",metric_definition="visit-weighted out-of-fold GLMM minus exposure-only GLM; negative favors GLMM",interval="paired building-cluster percentile bootstrap; eight clusters",caveat="Descriptive small-cluster uncertainty only; not independent-campus transfer, intervention efficacy or BNBU collision risk",results=result)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,indent=2))
if __name__=="__main__": main()
