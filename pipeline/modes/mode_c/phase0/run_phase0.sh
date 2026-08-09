#!/usr/bin/env bash
# Mode C Phase 0 — ONE short low-res replacement segment + VRAM sampling.
# Dry-run by default. Set CONFIRM_RUN=1 to actually run.
# Nothing here touches Mode A/B outputs. 27s generation is intentionally NOT invoked.
set -e

WAN_DIR="${WAN_DIR:-$PWD/Wan2.2}"
CKPT_DIR="${CKPT_DIR:-/transfer/wan/Wan2.2-Animate-14B}"
IN_DIR="${IN_DIR:-$PWD/input}"                 # expects driving_segment_phase0.mp4 + target_look_reference.png
OUT="${OUT:-$PWD/phase0_out}"
PROC="$OUT/process_results"
# Phase-0 LOW RES + SHORT. Lower these further first if you OOM. (portrait: H W)
RES_H="${RES_H:-832}"; RES_W="${RES_W:-480}"

mkdir -p "$OUT" "$PROC"
SEG="${SEG:-$IN_DIR/driving_segment_test2_phase0.mp4}"   # DEFAULT = your test2 window (test yours first).
# to test the mode_c.MP4 window instead:  SEG=$IN_DIR/driving_segment_phase0.mp4 CONFIRM_RUN=1 bash run_phase0.sh
REF="$IN_DIR/target_look_reference.png"

PREPROCESS=( python "$WAN_DIR/wan/modules/animate/preprocess/preprocess_data.py"
  --ckpt_path "$CKPT_DIR/process_checkpoint"
  --video_path "$SEG" --refer_path "$REF" --save_path "$PROC"
  --resolution_area "$RES_H" "$RES_W" --iterations 3 --k 7 --w_len 1 --h_len 1 --replace_flag )

# Low-VRAM generate flags. CONFIRM these are supported by your installed generate.py --help.
GENERATE=( python "$WAN_DIR/generate.py" --task animate-14B --ckpt_dir "$CKPT_DIR/"
  --src_root_path "$PROC/" --refert_num 1 --replace_flag --use_relighting_lora
  --offload_model True --convert_model_dtype --t5_cpu
  --save_file "$OUT/phase0_replacement.mp4" )

echo "=================== MODE C · PHASE 0 PLAN ==================="
echo "segment : $SEG"; echo "reference: $REF"; echo "res (HxW): ${RES_H}x${RES_W}  (lower if OOM)"
echo "output  : $OUT/phase0_replacement.mp4"
echo "--- preprocess ---"; printf '%q ' "${PREPROCESS[@]}"; echo
echo "--- generate ---";   printf '%q ' "${GENERATE[@]}";   echo
echo "==========================================================="

if [ "${CONFIRM_RUN:-0}" != "1" ]; then
  echo "DRY RUN. Set CONFIRM_RUN=1 to execute."; exit 0
fi

echo "[1/2] preprocess (pose + mask + background, replace mode)…"
"${PREPROCESS[@]}"

echo "[2/2] generate with GPU-memory sampler…"
# sample VRAM every 1s in the background, keep the peak
( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits; sleep 1; done ) > "$OUT/_vram_samples.txt" &
SAMP=$!
set +e
"${GENERATE[@]}"; GEN_RC=$?
set -e
kill "$SAMP" 2>/dev/null || true
PEAK=$(sort -n "$OUT/_vram_samples.txt" | tail -1)
echo "{\"generate_return_code\": $GEN_RC, \"vram_peak_mib\": ${PEAK:-null}, \"res_hxw\": \"${RES_H}x${RES_W}\", \"offload\": true}" > "$OUT/runtime.json"
echo "peak VRAM (MiB): ${PEAK:-unknown}   generate rc=$GEN_RC"
[ "$GEN_RC" != "0" ] && echo "NOTE: non-zero return (likely OOM). Lower RES_H/RES_W or switch to Wan2GP — an OOM here is a valid Phase 0 result."
echo "Now run: python measure_phase0.py"
