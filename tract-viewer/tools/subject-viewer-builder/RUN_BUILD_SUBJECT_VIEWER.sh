#!/usr/bin/env bash
set -euo pipefail

PY=/root/fsl/bin/python
DEST=/workspace/A2a/viewer_subject
SCRIPT=$DEST/build_subject_viewer.py
RAW=https://raw.githubusercontent.com/uMRI-web/uMRI-web.github.io/main/tract-viewer/tools/subject-viewer-builder/build_subject_viewer.py

echo "=== Subject Viewer Builder ==="
mkdir -p "$DEST"

if [ ! -x "$PY" ]; then
  echo "ERROR: $PY not found"
  exit 1
fi

echo "[0/3] Checking Python environment..."
$PY - <<'PY'
import nibabel, numpy, scipy
print("nibabel:", nibabel.__version__)
print("numpy:", numpy.__version__)
print("scipy:", scipy.__version__)
PY

if ! $PY -c "import skimage" >/dev/null 2>&1; then
  echo "[1/3] Installing scikit-image into FSL Python..."
  $PY -m pip install --no-cache-dir scikit-image
else
  echo "[1/3] scikit-image already installed"
fi

echo "[2/3] Downloading current builder script..."
wget -q -O "$SCRIPT" "$RAW"
test -s "$SCRIPT"

echo "[3/3] Building subject viewer assets and ZIP..."
$PY "$SCRIPT"

echo
echo "Done."
echo "Download this file from RunPod:"
echo "/workspace/A2a/viewer_subject/nougazounoatarashiibennkyoubonnver_READY.zip"
