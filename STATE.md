# proj5 – ComfyUI img2img (NSFW, local, no input metadata) – STATE

Date: 2026-09-19
Workspace: `/mnt/c/Users/steve/opencode/proj5` (only write here)
StabilityMatrix: `/mnt/c/Users/steve/Downloads/StabilityMatrix-win-x64/Data/`

## 1. User requirements (locked)
1. Stability Matrix installed under `.../StabilityMatrix-win-x64/Data/`
2. Use ComfyUI workflow for img2img: reference picture + prompt -> new picture based on reference + prompt
3. Run locally on own PC with downloaded local models
4. Input/reference picture has NO meta/prompts from creation – so cannot rely on original prompt / Pony score tags
5. Output will be NSFW

## 2. System inventory (verified 2026-09-19)
- GPU (from settings.json): NVIDIA GeForce RTX 4070 Ti SUPER, 16GB, CUDA
- ComfyUI: v0.36.0 in `Data/Packages/ComfyUI/`, Python 3.12.11, TorchIndex CUDA
- extra_model_paths.yaml correctly maps StableDiffusion, DiffusionModels, Lora, VAE, etc.
- ControlNet folder: EMPTY – no ControlNet workflow possible without download

### Checkpoints in `Data/Models/StableDiffusion/` (all ~6.5G, SDXL/Illustrious family):
- `waiNSFWIllustrious_v150.safetensors` ← PRIMARY CANDIDATE for NSFW img2img
- `waiIllustriousSDXL_v170.safetensors`
- `waiIllustriousSDXL_v160.safetensors`
- `prefectIllustriousXL_v70.safetensors`
- `hassakuXLIllustrious_v34.safetensors`
- `flatJusticeNoobaiV_v13.safetensors`
- `noobaiXLNAIXL_vPred10Version.safetensors`
- `ponyDiffusionV6XL_v6StartWithThisOne.safetensors`

### Other relevant models:
- `Data/Models/DiffusionModels/qwen_image_edit_2509_fp8_e4m3fn.safetensors` (20G)
- `Data/Models/TextEncoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` (8.8G)
- `Data/Models/VAE/qwen_image_vae.safetensors` (243M)
- `Data/Models/Lora/Qwen-Image-Edit-Lightning-4steps-V1.0.safetensors` (1.6G)
- `Data/Models/Lora/Expressive_H-000001.safetensors` (218M, NSFW helper)
- `Data/Models/Lora/Add_more_details_pony.safetensors`
- VAE folder has ONLY qwen VAE – SDXL checkpoints will use built-in VAE (normal)
- Embeddings, ClipVision: empty

## 3. Key clarification (important for req #4)
img2img in ComfyUI does NOT need input image metadata.
Standard flow: Load Image -> VAE Encode -> KSampler (denoise 0.55-0.75) with NEW prompt.
Pony score tags (`score_9, score_8up` etc.) are only needed if YOU choose Pony checkpoint.
We will NOT use Pony. We will use Illustrious NSFW model with plain natural-language + danbooru tags we write fresh.
So req #4 is solvable – no input meta required.

## 4. Plan – two options, need user pick
### Option A (Recommended, lightweight, matches all 5 reqs):
Classic SDXL img2img with `waiNSFWIllustrious_v150`
Nodes: LoadCheckpoint(waiNSFW) -> CLIPTextEncode(positive=new NSFW prompt, negative=blurry/low quality) -> LoadImage(reference) -> VAEEncode -> KSampler(euler_ancestral, 30 steps, cfg 6.5, denoise 0.65) -> VAEDecode -> SaveImage
Pros: 6.5GB, fast on 4070 Ti S, NSFW-tuned, no extra downloads, preserves composition via denoise slider
Cons: less precise edit-following than Qwen

### Option B (High-fidelity edit, heavier):
Qwen-Image-Edit 2509 fp8 + Qwen2.5-VL 7b + Qwen VAE + Lightning LoRA
Nodes: LoadDiffusionModel + LoadCLIP + LoadVAE + LoadLoRA(Lightning) -> CLIPTextEncode(edit instruction) -> ReferenceLatent / Qwen edit nodes -> Sampler (4-8 steps)
Pros: best at keeping character/pose while applying prompt change
Cons: ~29GB files, heavier VRAM, more complex workflow

## 5. Next steps (done – workflows built, user testing locally)
1. DONE: User picked Qwen-Image-Edit 2509 (Option B)
2. DONE: Built 3 API workflows in proj5/ (see Last status)
3. User runs locally in Stability Matrix -> ComfyUI, iterates seed/steps
4. Future: crop-zoom second pass for tiny/distant girls, optional 0.5x downscale after 4x upscale if files too large

## 6. Resume instructions for future session
- Workspace is ONLY `proj5/`. Read this file first.
- Do NOT scan outside except the StabilityMatrix Data paths listed above (read-only, except approved model downloads to Models/ESRGAN/).
- Current files: `workflow_img2img_qwen2509_api.json` (fast 4-step), `workflow_img2img_qwen2509_hidetail_api.json` (30-step, no LoRA), `workflow_img2img_qwen2509_hidetail_upscale_api.json` (hidetail + 4x-AnimeSharp, RECOMMENDED).
- Prompt is v3 GENERAL (any girls picture, explicit nipples, garment-type logic). Do not revert to greenhouse-specific v1/v2.
- Upscaler installed: `Data/Models/ESRGAN/4x-AnimeSharp.pth` (63.9MB). No other upscalers locally.

Last status: SAVED 2026-09-20 – corrected the two-reference workflow pose wiring to match the official Qwen 2509 blueprint: its scaled pose image now feeds both the sampler latent and Picture 1 conditioning. It is strictly SFW. `reference_pose.webp` controls output framing/pose; `reference_char.png` controls character identity/outfit. AWAITING USER LOCAL TEST.

Last status: WORKFLOW BUILT (Qwen2509 + Lightning 4-step), AWAITING LOCAL RUN.
Files in proj5/:
- STATE.md (this file)
- workflow_img2img_qwen2509_api.json (API format, 14 nodes, use via Queue Prompt / Load API workflow)
- TODO: user must save reference image as `reference.png` into `Packages/ComfyUI/input/` (copy from chat image), then load workflow.

Run steps:
1. Stability Matrix -> ComfyUI -> Launch (CUDA, 4070 Ti S)
2. In ComfyUI: Menu -> Load -> select workflow file OR paste API JSON via Queue
3. Ensure LoadImage node points to reference.png
4. Queue Prompt with steps=4, cfg=1, euler/simple, denoise=1.0, seed randomize
5. If too censored/unchanged: raise steps to 8, or disable Lightning LoRA (bypass node 89, use steps=20 cfg=4)
6. Output prefix: proj5_qwen_edit_
7. 2026-09-19 prompt v2: explicit 3-girl garment-preserving edit (foreground white blouse/corset/cape, middle purple dress/gloves, background blue cape/dress). Same fabric/colors/trim, just parted necklines. Fixes: background girl missed + outfit mismatch.
8. 2026-09-19 hidetail variant: `workflow_img2img_qwen2509_hidetail_api.json` (bypass Lightning LoRA node 89, UNET->ModelSampling directly, steps 30 cfg 4.0 euler/simple, +detail tokens). Use for sharp nipples/skin. No upscaler models locally (ESRGAN/RealESRGAN empty), so detail must come from full-step run + crop zoom.
9. 2026-09-19 upscale variant: `workflow_img2img_qwen2509_hidetail_upscale_api.json` = hidetail + tail nodes 20 UpscaleModelLoader (4x-AnimeSharp.pth) -> 21 ImageUpscaleWithModel (image from VAEDecode 8) -> SaveImage from 21. INSTALLED 2026-09-19: `Data/Models/ESRGAN/4x-AnimeSharp.pth` (63.9MB, from Kim2091/AnimeSharp HF). Ready to Queue – no more download needed. If node 20 red, restart ComfyUI to rescan upscale_models.
10. 2026-09-19 prompt v3 GENERAL: all 3 workflow files updated – no longer greenhouse/3-girl specific. Works on any picture with girls. Explicit visible nipples, no censorship. Garment logic: unbutton shirts/blouses, lift pullovers/T-shirts/dresses up, pull strapless down, slip/tear tight tops aside. Same fabric/colors/trim, no outfit swap.
11. 2026-09-20 two-reference workflow: `workflow_qwen2509_pose_character_hidetail_upscale_api.json` uses native `TextEncodeQwenImageEditPlus` multi-image support. Put `reference_pose.webp` and `reference_char.png` in `Packages/ComfyUI/input/`. The scaled pose image is the primary Qwen image reference and drives the sampler dimensions and composition; the character image is the optional second reference and supplies identity/outfit. It otherwise matches the 30-step hidetail + 4x-AnimeSharp workflow. Its prompt is SFW and explicitly prohibits nudity; Picture 1 is the strict pose/framing source, while Picture 2 must not supply pose/composition.
