#!/usr/bin/env bash
# Mode C Phase 0 — install Wan2.2-Animate + preprocess deps on w33108 (env: modec).
# Safe to re-run. Large downloads -> keep checkpoints on /transfer (~954G free).
set -e

WAN_DIR="${WAN_DIR:-$PWD/Wan2.2}"
CKPT_DIR="${CKPT_DIR:-/transfer/wan/Wan2.2-Animate-14B}"   # override if you prefer

echo "== 1. clone official Wan2.2 repo (reference interface) =="
[ -d "$WAN_DIR" ] || git clone https://github.com/Wan-Video/Wan2.2.git "$WAN_DIR"

echo "== 2. python deps (torch already present in modec; do NOT reinstall it) =="
pip install -r "$WAN_DIR/requirements.txt" || echo "!! review requirements.txt conflicts (esp. torch pin) before forcing"
pip install "huggingface_hub[cli]" onnxruntime-gpu insightface || true   # insightface = optional identity metric

echo "== 3. download Wan2.2-Animate-14B (includes process_checkpoint for DWPose/mask preprocess) =="
mkdir -p "$(dirname "$CKPT_DIR")"
huggingface-cli download Wan-AI/Wan2.2-Animate-14B --local-dir "$CKPT_DIR"

echo ""
echo "DONE. Set these before run_phase0.sh (or accept defaults):"
echo "  export WAN_DIR=$WAN_DIR"
echo "  export CKPT_DIR=$CKPT_DIR"
echo ""
echo "If the official 14B repo OOMs at 16GB, install the low-VRAM route instead:"
echo "  git clone https://github.com/deepbeepmeep/Wan2GP.git && see its README for Wan2.2-Animate"
