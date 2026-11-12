#!/usr/bin/env python3
"""Build a fully standalone / offline BNBU campus GLB viewer.

Usage:
  python make_viewer.py --model path/to/BNBU_v41_FULL_CAMPUS_EDITABLE.glb --version v41 --output BNBU_Campus_Viewer_v41.html

Never changes the input GLB. The viewer imports GLB 2.0 without external files.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path


def generate(model: Path, output: Path, version: str, template: Path, evidence: Path | None = None, strict: Path | None = None):
    template_text = template.read_text(encoding='utf-8')
    assert 'MODEL_BASE64' in template_text
    raw = model.read_bytes()
    if raw[:4] != b'glTF':
        raise ValueError('GLB magic header missing')
    mapping = {}
    if evidence and evidence.is_file():
        mapping = {x['editable_part']: {'confidence': x.get('confidence', ''),'source': x.get('source', ''),'eligible': x.get('bird_strike_metric_eligible',False)}
                   for x in json.loads(evidence.read_text(encoding='utf-8'))
                   if x.get('editable_part')}
    replace = {
        '__VERSION__': version.replace('"', '').replace("'", ''),
        '__EVIDENCE_JSON__': json.dumps(mapping, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/'),
        '__MODEL_BASE64__': base64.b64encode(raw).decode('ascii'),
        '__STRICT_BASE64__': base64.b64encode(strict.read_bytes()).decode('ascii') if strict else base64.b64encode(raw).decode('ascii'),
    }
    for a, b in replace.items():
        template_text = template_text.replace(a, b)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template_text, encoding='utf-8')
    print(json.dumps({'html': str(output), 'html_bytes': output.stat().st_size,
                      'model_bytes': len(raw), 'model_sha256': hashlib.sha256(raw).hexdigest(),
                      'version': version}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--template', type=Path, default=Path(__file__).with_name('viewer_template.html'))
    p.add_argument('--evidence', type=Path)
    p.add_argument('--strict', type=Path)
    a = p.parse_args()
    generate(a.model, a.output, a.version, a.template, a.evidence, a.strict)