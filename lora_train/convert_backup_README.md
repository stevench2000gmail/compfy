# OneTrainer backup -> LoRA recovery (fanta-chr002-ressa, 2026-09-28)

## What happened
Training ran to 100% (12 epochs), then crashed in `trainer.end()`:
`NotImplementedError: Unsupported LoRA output format: SAFETENSORS`
(`modules/modelSaver/mixin/LoRASaverMixin.py:184`).

Root cause: train config had `output_model_format: SAFETENSORS`, which is only
valid for `EMBEDDING` training (`modules/util/enum/ModelType.py:272-276`).
Valid SDXL LoRA formats are `DIFFUSERS_LORA, KOHYA_LORA, ORIGINAL_LORA,
COMFY_LORA, LEGACY_LORA` (`ModelType.py:222-243`). Because the exception
escaped `GenericTrainer.end()`, the UI never reached `on_training_stopped`
(`TrainUIController.py:261`), so no completion message and `Stop Training`
stayed stuck. Epoch saves failed the same way (caught in `GenericTrainer.py`).

Weights were NOT lost: the `INTERNAL` backup saved fine:
`workspace/run/backup/2026-09-28_11-56-33-backup-1008-12-0/lora/lora.safetensors`
(245M, 3177 tensors, canonical `text_encoder/unet` keys).

## Why Convert UI failed
`ConvertModelUIController.py:83` always passes a dummy
`EmbeddingName(uuid4(), input)`. `GenericLoRAModelLoader.py:54` then forces an
embedding load, which fails for this backup (no `embeddings/<uuid>.safetensors`
inside). Second row of the Convert window is also mislabeled `Model Type`
(`BaseConvertModelUIView.py:43`) — it is really Training Method, set to `LoRA`.

## Fix (no retrain)
Files:
- `lora_train/convert_backup_to_kohya.py` — loads the canonical backup dict
  and saves via `StableDiffusionXLLoRASaver` directly, skipping the
  base-model/embedding loader path.
- `lora_train/convert_backup_to_kohya.sh` — WSL wrapper that calls
  OneTrainer's venv python (`Data/Packages/OneTrainer/venv/Scripts/python.exe`).
  Do NOT use the raw `Assets/Python/...` exe (missing deps) or system python.

Usage (WSL):
```bash
cd /mnt/c/Users/steve/opencode/proj5/lora_train
chmod +x convert_backup_to_kohya.sh
# defaults: known backup -> Data/Models/Lora/fanta-chr002-ressa.safetensors, KOHYA_LORA
./convert_backup_to_kohya.sh
# explicit:
./convert_backup_to_kohya.sh <backup_dir_or_lora.safetensors> <output.safetensors> [KOHYA_LORA|COMFY_LORA|DIFFUSERS_LORA|ORIGINAL_LORA|LEGACY_LORA]
```

Usage (Windows cmd, from `Data/Packages/OneTrainer`):
```bat
venv\Scripts\python.exe -X utf8 C:\Users\steve\opencode\proj5\lora_train\convert_backup_to_kohya.py <backup> <output> <FORMAT>
```

## Verify
- Output ~123MB `.safetensors`, 3177 tensors.
- Keys should be Kohya style: `lora_unet_...`, `lora_te1_...` with
  `lora_down/lora_up`. Check with the snippet in the wrapper history or:
  `python3 -c` read header via `struct`+`json` (safetensors header) and list keys.
- ComfyUI test: `workflow_sdxl_lora_character_test_api.json`
  (waiNSFW + LoRA 0.6–1.0).

## Prevent next time
In Train tab -> `model` tab set `Output Format` to `Kohya` (best ComfyUI/A1111
compat; `Comfy` also OK) and Save config before pressing Train.
