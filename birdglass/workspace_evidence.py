"""Export the canonical, public subset of pane evidence for the campus viewer."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import quote

from .evidence import EvidenceTier, Measurement
from .glass_observation import GlassObservation
from .pane_registry import PaneGlassObservation, PaneIdentity, PaneRegistry, audit_glass_evidence

VEGETATION_IDS = {
    "0_5m": "tree_cover_0_5_m", "5_25m": "tree_cover_5_25_m",
    "25_100m": "tree_cover_25_100_m", "100m_1km": "tree_cover_100_1000_m",
    "1_10km": "tree_cover_1000_10000_m",
}
RISK_FACTS = {
    "glass_contact_risk": "glass_contact_given_approach",
    "carcass_detection_risk": "detected_carcass_presence",
}
OPTICAL_CLASSES = {
    "transparent", "reflective", "mirrored", "reflective_and_transparent",
    "frosted_translucent", "opaque_spandrel",
}
KEYS = ("pane_id", "building_id", "facade_id", "model_version")


def _time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Workspace timestamps require a time-zone offset")
    return parsed


def _key(value: dict) -> PaneIdentity:
    return PaneIdentity(**{key: value[key] for key in KEYS})


def _fact(identifier, unit=None, *, value=None, status="missing", at=None,
          expiry=None, tier="unknown", sources=(), view_id=None):
    return {
        "id": identifier, "value": value, "unit": unit, "status": status,
        "observed_at": at, "expires_at": expiry, "evidence_tier": tier,
        "source_ids": sorted(set(sources)),
        "view_id": view_id,
    }


def _digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _competing_sources(conflicts):
    source_ids = {source for row in conflicts for source in row["source_ids"]}
    if len(source_ids) < 2:
        source_ids.update("evidence:" + source for row in conflicts for source in row["evidence_ids"])
    return source_ids


def _glass_facts(rows, conflicts):
    usable = [row for row in rows if row.source_kind != "clip_screen"]
    latest_first = sorted(usable, key=lambda row: row.observed_at, reverse=True)
    appearances = [row for row in latest_first if row.observation.visual_class_confirmed
                   and row.observation.visual_class in OPTICAL_CLASSES]
    appearance_conflicts = [row for row in conflicts if row["field"] == "visual_class"]
    if appearance_conflicts:
        yield _fact("optical_mechanism", status="conflict", sources=_competing_sources(appearance_conflicts))
    elif len({row.observation.visual_class for row in appearances}) > 1:
        yield _fact("optical_mechanism", status="withheld",
                    sources={row.source_id for row in appearances})
    elif not appearances:
        yield _fact("optical_mechanism")
    else:
        appearance = appearances[0]
        observation = appearance.observation
        tier = observation.visual_class_evidence_tier
        yield _fact(
            "optical_mechanism", value=observation.visual_class,
            status="inferred" if tier in {EvidenceTier.PROXY, EvidenceTier.ASSUMPTION} else "observed",
            at=appearance.observed_at.isoformat(),
            tier=EvidenceTier.LOCAL_SURVEY.value if tier == EvidenceTier.UNKNOWN else tier.value,
            sources=(appearance.source_id, observation.visual_class_source_id),
        )
    for fact_id, attribute, unit in (
        ("exterior_vlr", "exterior_vlr_pct", "%"),
        ("exterior_vlt", "exterior_vlt_pct", "%"),
    ):
        competing = [row for row in conflicts if row["field"] == attribute]
        if competing:
            yield _fact(fact_id, unit, status="conflict",
                        sources=_competing_sources(competing))
            continue
        for row in latest_first:
            value = getattr(row.observation, attribute)
            if value is not None and value.available and value.tier != EvidenceTier.UNKNOWN:
                yield _fact(
                    fact_id, unit, value=value.value,
                    status="observed" if row.source_kind == "instrument" else "inferred",
                    at=row.observed_at.isoformat(), tier=value.tier.value,
                    sources=(row.source_id, value.source_id),
                )
                break
        else:
            yield _fact(fact_id, unit)


def _vegetation_facts(vegetation):
    land = vegetation.get("land_cover", {})
    for band, identifier in VEGETATION_IDS.items():
        value = land.get("bands", {}).get(band, {}).get("tree_canopy_cover_percent")
        if value is None or land.get("status") != "reviewed":
            yield _fact(identifier, "fraction")
        else:
            yield _fact(
                identifier, "fraction", value=value / 100,
                status="inferred" if land["evidence_tier"] in {"proxy", "assumption"} else "observed",
                at=land["recorded_at"], tier=land["evidence_tier"], sources=(land["source_id"],),
            )
    views = vegetation.get("reflection_views", [])
    if not views:
        yield _fact("reflected_vegetation", "fraction")
    for row in views:
        value = row.get("reflected_vegetation_share")
        reviewed = row.get("status") == "reviewed" and value is not None
        status = "inferred" if row["evidence_tier"] in {"proxy", "assumption"} else "observed"
        yield _fact("reflected_vegetation:" + quote(row["view_id"], safe="-_.!~*'()"), "fraction",
                    view_id=row["view_id"], value=value if reviewed else None,
                    status=status if reviewed else "missing", at=row.get("recorded_at"),
                    tier=row["evidence_tier"], sources=(row["source_id"],) if row.get("source_id") else ())


def export_workspace(
    report_bytes: bytes, registry: PaneRegistry, binding_file: dict, *,
    vegetation_reports=(), glass_rows=(),
) -> dict:
    report = json.loads(report_bytes)
    if report["schema_version"] != 1 or report["evidence_kind"] not in {"synthetic", "bnbu_monitoring"}:
        raise ValueError("Unsupported monitoring report")
    kind = "synthetic" if report["evidence_kind"] == "synthetic" else "field"
    if registry.dataset_kind != kind or binding_file["dataset_kind"] != kind:
        raise ValueError("Registry, report and mapping dataset kinds must agree")
    validity_end = _time(binding_file["valid_until"])
    panes = {}
    for row in report["panes"]:
        identity = _key(row["pane"])
        if identity in panes:
            raise ValueError("Duplicate pane in canonical monitoring report")
        panes[identity] = row
    vegetation = {}
    for row in vegetation_reports:
        identity = _key(row["pane"])
        if row["dataset_kind"] != kind or identity not in panes or identity in vegetation:
            raise ValueError("Vegetation evidence must uniquely match the canonical pane and dataset kind")
        vegetation[identity] = row
    glass = defaultdict(list)
    conflicts = defaultdict(list)
    glass_rows = tuple(glass_rows)
    for row in glass_rows:
        if row.identity not in panes:
            raise ValueError("Glass evidence does not match a canonical pane")
        glass[row.identity].append(row)
    for conflict in audit_glass_evidence(registry, glass_rows):
        conflicts[_key(conflict)].append(conflict)
    bindings = []
    object_names, pane_ids = set(), set()
    for row in binding_file["bindings"]:
        identity = _key(row["pane"])
        pane = registry.require(identity, field_verified=kind == "field")
        monitor = panes.get(identity)
        if monitor is None or pane.geometry_source_id != monitor["pane"]["registration_source_id"]:
            raise ValueError("Object bindings require the exact pane and matching geometry source")
        if not all((pane.floor, pane.bay, row["object_name"].strip(), row["mapping_source_id"].strip())):
            raise ValueError("Object bindings require a physical locator and mapping source")
        if row["object_name"] in object_names or identity.pane_id in pane_ids:
            raise ValueError("3D object and pane binding must be one to one")
        if _time(row["mapped_at"]) > validity_end:
            raise ValueError("Mapping timestamp is after package validity")
        object_names.add(row["object_name"])
        pane_ids.add(identity.pane_id)
        evidence = [*_glass_facts(glass[identity], conflicts[identity]),
                    *_vegetation_facts(vegetation.get(identity, {}))]
        approaches = monitor["approaches"]
        sessions = monitor.get("video_sessions", ())
        if any(_key(source) != identity for source in [*approaches, *sessions]):
            raise ValueError("Monitoring sources do not match the bound pane identity")
        complete_zero = bool(sessions) and all(row["complete_session_approach_count"] == 0 for row in sessions)
        count = len(approaches) if approaches or complete_zero else None
        timestamp = max((row["gate_at"] for row in approaches), key=_time, default=None)
        counted_sources = approaches
        if complete_zero:
            timestamp = max((row["end"] for row in sessions), key=_time)
            counted_sources = sessions
        count_tier = "unknown"
        if count is not None:
            count_tier = "local_survey" if kind == "field" else "assumption"
        evidence.append(_fact(
            "approach_count", "count", value=count, at=timestamp, tier=count_tier,
            status={"unknown":"missing","assumption":"inferred","local_survey":"observed"}[count_tier],
            sources={row["source_id"] for row in counted_sources},
        ))
        for fact_id, endpoint in RISK_FACTS.items():
            if monitor["risk_predictions"][endpoint]["value"] is not None:
                raise ValueError("Workspace v1 supports only withheld numerical risk")
            evidence.append(_fact(fact_id, status="withheld", sources=(report["evidence_snapshot_id"],)))
        evidence.append(_fact("local_treatment_effect", status="withheld"))
        if any(fact["observed_at"] and _time(fact["observed_at"]) > validity_end for fact in evidence):
            raise ValueError("Evidence timestamp is after package validity")
        bindings.append({
            "object_name": row["object_name"], "pane": identity.as_dict(),
            "floor": pane.floor, "bay": pane.bay, "mapping_source_id": row["mapping_source_id"],
            "facts": evidence,
        })
    return {
        "schema_version": 1, "scene_version": binding_file["scene_version"], "dataset_kind": kind,
        "evidence_snapshot_id": report["evidence_snapshot_id"], "report_sha256": sha256(report_bytes).hexdigest(),
        "input_sha256": {
            "registry": _digest(registry.as_dict()), "mapping": _digest(binding_file),
            "vegetation": _digest([vegetation[key] for key in sorted(vegetation,key=lambda identity: identity.pane_id)]),
            "glass": _digest([row.as_dict() for row in sorted(glass_rows,key=lambda row: row.evidence_id)]),
        },
        "valid_until": binding_file["valid_until"], "bindings": bindings,
    }


def _glass_from_json(row):
    """Read the public optical subset of PaneGlassObservation.as_dict()."""
    glass = row["observation"]
    measurements = {}
    for field in ("exterior_vlr_pct", "exterior_vlt_pct"):
        value = glass.get(field)
        if value is not None:
            fields = dict(value)
            fields["tier"] = EvidenceTier(fields.pop("evidence_tier"))
            measurements[field] = Measurement(**fields)
    observation = GlassObservation(
        facade_id=glass["facade_id"], visual_class=glass["provisional_visual_class"],
        visual_class_evidence_tier=EvidenceTier(glass["visual_class_evidence_tier"]),
        visual_class_source_id=glass["visual_class_source_id"], reviewed_by_human=glass["reviewed_by_human"],
        surface_treatment=glass["surface_treatment"], coating_position=glass["coating_position"],
        photo_ids=tuple(glass["photo_ids"]), specification_id=glass["specification_id"],
        observer_id=glass["observer_id"], **measurements,
    )
    fields = {key: value for key, value in row.items() if key not in {"identity", "observation", "observed_at", "spectrum"}}
    return PaneGlassObservation(
        identity=_key(row["identity"]), observed_at=_time(row["observed_at"]), observation=observation, **fields,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("registry", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--vegetation-report", action="append", type=Path, default=[])
    parser.add_argument("--glass-observations", type=Path)
    args = parser.parse_args()
    try:
        read = lambda path: json.loads(path.read_text(encoding="utf-8"))
        data = export_workspace(
            args.report.read_bytes(), PaneRegistry.from_dict(read(args.registry)), read(args.mapping),
            vegetation_reports=[read(path) for path in args.vegetation_report],
            glass_rows=[_glass_from_json(row) for row in read(args.glass_observations)]
            if args.glass_observations else (),
        )
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
