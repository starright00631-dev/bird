"""Leakage-safe splits of the published 3D-POP trial metadata.

3D-POP source: Naik et al., CVPR 2023; metadata originally published at
https://github.com/alexhang212/Dataset-3DPOP/blob/main/Dataset/Pop3DMetadata.csv

Grouping reflects **source-documented subject-session labels and video IDs**,
not globally verified biological identity across separate dates. Identical
video filenames without matching date are NOT assumed to denote one recording.
"""
from collections import defaultdict, Counter
import csv
from io import StringIO

_REQUIRED = {"Sequence", "ViconTrial", "SonyVideoName", "IndividualNum", "Date", "Subjects"}


def read_3dpop_metadata(csv_source):
    """Read and audit an original metadata CSV string; fail on ambiguity."""
    reader = csv.DictReader(StringIO(csv_source))
    if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("Missing or duplicate CSV headers")
    if not _REQUIRED.issubset(reader.fieldnames):
        raise ValueError("3D-POP metadata fields missing")
    rows = []
    seen_sequence = set()
    for row in reader:
        if None in row or any(row.get(k) is None for k in _REQUIRED):
            raise ValueError("Broken metadata row")
        sequence = str(row["Sequence"]).strip()
        date = str(row["Date"]).strip()
        trial = str(row["ViconTrial"]).strip()
        video = str(row["SonyVideoName"]).strip()
        subjects = tuple(s.strip() for s in row["Subjects"].split(";"))
        try:
            n = int(row["IndividualNum"])
        except (ValueError, TypeError):
            raise ValueError("Invalid IndividualNum") from None
        if (not sequence or not date or not trial or not video or
            sequence in seen_sequence or
            not subjects or any(not s for s in subjects) or
            len(set(subjects)) != len(subjects) or n != len(subjects)):
            raise ValueError("Ambiguous or inconsistent trial and subject count")
        seen_sequence.add(sequence)
        rows.append({
            "sequence": sequence,
            "date": date,
            "trial": trial,
            "video": video,
            "n_subjects": n,
            "subjects": subjects,
        })
    if not rows:
        raise ValueError("Empty metadata")
    return rows


def _components(rows):
    parent = {r["sequence"]: r["sequence"] for r in rows}
    def root(s):
        while parent[s] != s:
            parent[s] = parent[parent[s]]
            s = parent[s]
        return s
    def join(a,b):
        x,y = root(a),root(b)
        if x != y:
            parent[max(x,y)] = min(x,y)
    known_subjects = defaultdict(list)
    known_recordings = defaultdict(list)
    for row in rows:
        for identity in row["subjects"]:
            # The source names include dates; cross-date biological identity
            # cannot be inferred, even when numeric pigeon labels match.
            known_subjects[identity].append(row["sequence"])
        video_key = (row["date"], row["trial"], row["video"])
        known_recordings[video_key].append(row["sequence"])
    for bucket in list(known_subjects.values()) + list(known_recordings.values()):
        for seq in bucket[1:]:
            join(bucket[0],seq)
    groups = defaultdict(list)
    for row in rows:
        groups[root(row["sequence"])].append(row["sequence"])
    return tuple(tuple(sorted(s,key=lambda x:int(x) if x.isdigit() else x))
                 for _,s in sorted(groups.items()))


def audit_metadata(rows):
    """Actual source counts, not generalized trajectory skill or outcomes."""
    recordings = Counter((r["date"],r["trial"],r["video"]) for r in rows)
    subjects = Counter(s for row in rows for s in row["subjects"])
    groups = _components(rows)
    return {
        "n_metadata_rows":len(rows),
        "n_subject_session_labels":len(subjects),
        "n_subject_labels_in_multiple_rows":sum(v>1 for v in subjects.values()),
        "n_duplicate_recording_rows":sum(v-1 for v in recordings.values()),
        "n_independent_source_groups":len(groups),
        "group_sizes_sorted":sorted((len(g) for g in groups),reverse=True),
        "cross_date_biological_identity_certified":False,
        "raw_3d_tracks_available_in_metadata":False,
        "source":"Naik et al. 3D-POP trial registry (GitHub, CVPR 2023)",
    }


def component_fold_assignment(rows, n_folds=5):
    """Return sequence -> fold, with zero documented subject/video overlap.

    Greedy bin packing of connected source groups. This is only a
    *known-identity leakage guard*, not proof of cross-session novelty.
    """
    groups = list(_components(rows))
    if n_folds < 2 or n_folds > len(groups):
        raise ValueError("Folds must be 2..number of independent source groups")
    indexed = sorted(groups,key=lambda g:(-len(g),g[0]))
    folds = [[] for _ in range(n_folds)]
    for group in indexed:
        fold = min(range(n_folds), key=lambda i:(len(folds[i]),i))
        folds[fold].extend(group)
    assignment = {sequence:i for i,fold in enumerate(folds) for sequence in fold}
    if len(assignment) != len(rows):
        raise ValueError("A source trial was not assigned exactly once")
    for row in rows:
        for other in rows:
            if assignment[row["sequence"]] == assignment[other["sequence"]]:
                continue
            overlap = bool(set(row["subjects"]).intersection(other["subjects"]))
            same_video = (row["date"],row["trial"],row["video"]) == (
                 other["date"],other["trial"],other["video"])
            if overlap or same_video:
                raise AssertionError("Leakage across fold assignments")
    return assignment
