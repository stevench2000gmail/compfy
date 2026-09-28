#!/usr/bin/env bash
set -euo pipefail

# Queue pose validation or generation from a pipe-delimited manifest:
# label|input_image|pose_description
# Optional third argument: request config JSON used only for generate mode.
mode=${1:?usage: run_pose_batch.sh validate|generate manifest.tsv [request.json]}
manifest=${2:?usage: run_pose_batch.sh validate|generate manifest.tsv [request.json]}
config=${3:-}
api_url=${COMFY_API_URL:-http://172.30.240.1:8188}

case "$mode" in
  validate) workflow="workflow_sdpose_pose_test_only_api.json" ;;
  generate) workflow="workflow_qwen_detail_sdpose_pose_correct_api.json" ;;
  *)
    printf 'mode must be validate or generate\n' >&2
    exit 2
    ;;
esac

if [ "$mode" = generate ] && [ -n "$config" ]; then
  character=$(jq -r '.character' "$config")
  outfit=$(jq -r '.outfit' "$config")
  item=$(jq -r '.item' "$config")
  intention=$(jq -r '.intention' "$config")
  quality=$(jq -r '.quality_prefix' "$config")
  negative_cfg=$(jq -r '.negative' "$config")
  steps_cfg=$(jq -r '.steps' "$config")
  cfg_cfg=$(jq -r '.cfg' "$config")
  denoise_cfg=$(jq -r '.denoise' "$config")
  sampler_cfg=$(jq -r '.sampler_name' "$config")
  scheduler_cfg=$(jq -r '.scheduler' "$config")
  control_cfg=$(jq -r '.control_strength' "$config")
  ipadapter_cfg=$(jq -r '.ipadapter_weight' "$config")
  width_cfg=$(jq -r '.width' "$config")
  height_cfg=$(jq -r '.height' "$config")
  seed_base_cfg=$(jq -r '.seed_base' "$config")
fi

index=0
while IFS='|' read -r label image pose; do
  [ -z "$label" ] && continue
  case "$label" in \#*) continue ;; esac

  if [ "$mode" = validate ]; then
    payload=$(jq -c --arg image "$image" --arg prefix "proj5_sdpose_${label}_pose_test_preview" \
      '."1".inputs.image = $image | ."7".inputs.filename_prefix = $prefix | {prompt: .}' \
      "$workflow")
  else
    if [ -n "$config" ]; then
      character="$character"
      outfit="$outfit"
      item="$item"
      intention="$intention"
      quality="$quality"
      negative="$negative_cfg"
      steps="$steps_cfg"
      cfg="$cfg_cfg"
      denoise="$denoise_cfg"
      sampler="$sampler_cfg"
      scheduler="$scheduler_cfg"
      control_strength="$control_cfg"
      ipadapter_weight="$ipadapter_cfg"
      width="$width_cfg"
      height="$height_cfg"
      seed_base="$seed_base_cfg"
    else
      character="1girl, solo, adult red-haired female fantasy knight, auburn hair, blue eyes"
      outfit="intricate black and dark-red military dress with gold trim, red cape, black gloves, short military skirt, visible bare upper thighs between the skirt and thigh-high armored boots"
      item=""
      intention=""
      quality="masterpiece, best quality, detailed anime illustration"
      negative="worst quality, low quality, lowres, blurry, jpeg artifacts, deformed, bad anatomy, extra limbs, extra fingers, missing fingers, cropped, multiple people, two girls, duplicate character, clone, nude, nudity, naked, topless, exposed breasts, nipples, see-through clothing, NSFW, explicit"
      steps=40
      cfg=5.0
      denoise=1.0
      sampler="dpmpp_2m"
      scheduler="karras"
      control_strength=1.4
      ipadapter_weight=0.05
      width=768
      height=1152
      seed_base=987654321
    fi
    positive="${quality}, ${character}, ${outfit}, ${item}, full body, ${intention}, ${pose}"
    seed=$((seed_base + index))
    payload=$(jq -c --arg image "$image" --arg text "$positive" --arg negative "$negative" --arg prefix "proj5_sdpose_${label}_bare_thighs_transparent" \
      --argjson steps "$steps" --argjson cfg "$cfg" --argjson denoise "$denoise" \
      --arg sampler "$sampler" --arg scheduler "$scheduler" \
      --argjson control_strength "$control_strength" --argjson ipadapter_weight "$ipadapter_weight" \
      --argjson width "$width" --argjson height "$height" --argjson seed "$seed" \
      '."1".inputs.image = $image
      | ."3".inputs.width = $width | ."3".inputs.height = $height
      | ."9".inputs.text = $text | ."10".inputs.text = $negative
      | ."13".inputs.weight = $ipadapter_weight
      | ."16".inputs.strength = $control_strength
      | ."18".inputs.seed = $seed | ."18".inputs.steps = $steps | ."18".inputs.cfg = $cfg
      | ."18".inputs.sampler_name = $sampler | ."18".inputs.scheduler = $scheduler
      | ."18".inputs.denoise = $denoise
      | ."25".inputs.width = $width | ."25".inputs.height = $height
      | ."23".inputs.filename_prefix = $prefix | {prompt: .}' \
      "$workflow")
    index=$((index + 1))
  fi
  printf '%s' "$payload" | curl --fail --silent --show-error --header "Content-Type: application/json" --data-binary @- "$api_url/prompt"
done < "$manifest"
