#!/usr/bin/env bash
set -euo pipefail

PY=/root/fsl/bin/python
SCRIPT=/workspace/A2a/viewer_subject/build_subject_viewer.py

echo "=== Subject Viewer Builder ==="

if [ ! -x "$PY" ]; then
  echo "ERROR: $PY not found"
  exit 1
fi

$PY - <<'PY'
import nibabel, numpy, scipy
print("nibabel:", nibabel.__version__)
print("numpy:", numpy.__version__)
print("scipy:", scipy.__version__)
PY

if ! $PY -c "import skimage" >/dev/null 2>&1; then
  echo "Installing scikit-image into FSL Python..."
  $PY -m pip install --no-cache-dir scikit-image
fi

if [ ! -f "$SCRIPT" ]; then
  echo "ERROR: builder script not found: $SCRIPT"
  exit 1
fi

$PY "$SCRIPT"
