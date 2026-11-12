#!/usr/bin/env sh
set -eu
python source/build_v77.py
python source/verify_v77.py
python source/render_v77.py
python source/make_viewer_v77.py
python source/test_viewer_v77.py