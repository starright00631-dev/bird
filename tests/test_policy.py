import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from textwrap import dedent

import pytest
from birdglass.contact import RectPane
from birdglass.policy import Scenario,assess,abstention_gate

def test_paired_joint_counterfactual_and_deployment_gate():
    panes=[RectPane("g",0,-1,1,0,2)]
    flights=[((-1,0,1),(5,0,0),(2,0,1),.04,.3,1.)]
    scenarios=[Scenario("unfit",.14,4.5,12.,7.,{"g":0.})]
    x=assess(panes,flights,scenarios,{"g":.8},seed=9)
    y=assess(panes,flights,scenarios,{"g":.8},seed=9)
    assert x==y
    assert not abstention_gate(x)["authorized_for_deployment"]

def test_policy_cannot_mark_opaque():
    panes=[RectPane("wall",0,-1,1,0,2,"opaque"),
           RectPane("g",0,1,2,0,2)]
    flights=[((-1,0,1),(5,0,0),(2,0,1),.04,.3,1.)]
    scenarios=[Scenario("unfit",.14,4.5,12.,7.,{})]
    with pytest.raises(ValueError):
        assess(panes,flights,scenarios,{"wall":.5})

def test_zero_effect_matches_paired_baseline():
    panes=[RectPane("g",0,-1,1,0,2)]
    flights=[((-1,0,1),(5,0,0),(2,0,1),.04,.3,1.)]
    rows=assess(panes,flights,[Scenario("same",.1,4.,10.,6.,{"g":.2})],{},seed=17)
    assert rows[0]["total_contact_reduction"]==pytest.approx(0.)
    assert rows[0]["glass_before"]==rows[0]["glass_after"]


def test_paired_draws_are_stable_across_processes_and_pane_orders():
    program = dedent("""\
        import json
        from birdglass.contact import RectPane
        from birdglass.policy import Scenario, assess

        panes = [RectPane("A", 0, -.4, .4, .8, 1.2),
                 RectPane("B", 0, 3, 4, .8, 1.2)]
        flights = [((-4, 0, 1), (4, 0, 0), (2, 0, 1), .04, .2, 1.)]
        hypotheses = [Scenario("synthetic", 0., 5., 20., 7., {"A": .7})]
        forward = assess(panes, flights, hypotheses, {}, seed=1)
        backward = assess(panes[::-1], flights, hypotheses, {}, seed=1)
        print(json.dumps([forward, backward]))
    """)
    outputs = [
        subprocess.check_output(
            [sys.executable, "-c", program],
            env={**os.environ, "PYTHONHASHSEED": hash_seed},
            text=True,
        )
        for hash_seed in ("1", "3")
    ]
    assert outputs[0] == outputs[1]
    forward, backward = json.loads(outputs[0])
    assert forward == backward
    assert forward[0]["glass_before"] == 0.0


def test_avoidance_can_transfer_contact_to_an_opaque_neighbor():
    panes = [
        RectPane("A", 0, -.4, .4, .8, 1.2),
        RectPane("wall", 0, -.4, .4, .65, .75, "opaque"),
        RectPane("unused_wall", 0, 3, 4, .8, 1.2, "opaque"),
    ]
    flights = [((-4, 0, 1), (4, 0, 0), (2, 0, 1), .04, .2, 1.)]
    scenarios = [Scenario("transfer", 0., 5., 20., 7., {})]
    row, = assess(panes, flights, scenarios, {"A": 1.}, dt=.025)

    assert row["pane_transfer"] == {"A": -1.}
    assert row["opaque_pane_transfer"] == {"wall": 1., "unused_wall": 0.}
    assert row["total_contact_reduction"] == pytest.approx(0.)


def test_stress_cli_binds_synthetic_snapshot_and_model_to_output(tmp_path):
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, str(root / "scripts/reproduce_policy_stress.py"),
         "--out-dir", str(tmp_path)],
        cwd=tmp_path,
        check=True,
    )

    manifest = json.loads((tmp_path / "manifest.json").read_bytes())
    output = (tmp_path / "policy_stress.json").read_bytes()
    snapshot = manifest["snapshot"]
    assert snapshot["sha256"] == sha256((root / snapshot["path"]).read_bytes()).hexdigest()
    assert manifest["outputs_sha256"] == {"policy_stress.json": sha256(output).hexdigest()}
    for path, digest in manifest["model_files_sha256"].items():
        assert digest == sha256((root / path).read_bytes()).hexdigest()

    result = json.loads(output)
    assert result["snapshot_id"] == snapshot["id"]
    assert result["evidence_kind"] == snapshot["kind"] == "synthetic"
    assert len(result["runs"]) == 4
    assert all(not run["gate"]["authorized_for_deployment"] for run in result["runs"])
