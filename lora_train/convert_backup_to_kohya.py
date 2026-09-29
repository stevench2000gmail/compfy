# Direct INTERNAL backup -> LoRA file, bypasses Convert UI embedding bug.
# Usage:
#   Windows cmd (from Data/Packages/OneTrainer):
#     venv\Scripts\python.exe -X utf8 C:\Users\steve\opencode\proj5\lora_train\convert_backup_to_kohya.py [backup_dir_or_file] [output.safetensors] [KOHYA_LORA|COMFY_LORA|DIFFUSERS_LORA|ORIGINAL_LORA|LEGACY_LORA]
#   WSL (preferred, use the wrapper):
#     ./convert_backup_to_kohya.sh [backup_dir_or_file] [output.safetensors] [FORMAT]
# Defaults below reproduce the 2026-09-28 fanta-chr002-ressa recovery.
import os
import sys

ONETRAINER_ROOT = r"C:\Users\steve\Downloads\StabilityMatrix-win-x64\Data\Packages\OneTrainer"
DEFAULT_BACKUP = r"C:\Users\steve\Downloads\StabilityMatrix-win-x64\Data\Packages\OneTrainer\workspace\run\backup\2026-09-28_11-56-33-backup-1008-12-0"
DEFAULT_OUTPUT = r"C:\Users\steve\Downloads\StabilityMatrix-win-x64\Data\Models\Lora\fanta-chr002-ressa.safetensors"
DEFAULT_FORMAT = "KOHYA_LORA"

sys.path.insert(0, ONETRAINER_ROOT)
sys.path.insert(0, os.path.join(ONETRAINER_ROOT, "scripts"))
os.chdir(ONETRAINER_ROOT)

from util.import_util import script_imports
script_imports()

from safetensors.torch import load_file

from modules.model.StableDiffusionXLModel import StableDiffusionXLModel
from modules.modelSaver.stableDiffusionXL.StableDiffusionXLLoRASaver import StableDiffusionXLLoRASaver
from modules.util.enum.DataType import DataType
from modules.util.enum.ModelFormat import ModelFormat
from modules.util.enum.ModelType import ModelType

src_input = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BACKUP
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
format_name = (sys.argv[3] if len(sys.argv) > 3 else DEFAULT_FORMAT).upper()

# Accept either the backup folder or the lora.safetensors file inside it.
if os.path.isdir(src_input):
    src = os.path.join(src_input, "lora", "lora.safetensors")
else:
    src = src_input
print("Loading " + src)
state_dict = load_file(src)
print(f"Loaded {len(state_dict)} tensors")

model = StableDiffusionXLModel(model_type=ModelType.STABLE_DIFFUSION_XL_10_BASE)
model.lora_state_dict = state_dict
model.additional_embeddings = []
model.text_encoder_1_lora = None
model.text_encoder_2_lora = None
model.unet_lora = None

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
output_format = getattr(ModelFormat, format_name, None)
if output_format is None:
    raise SystemExit(f"Unknown format {format_name!r}. Use KOHYA_LORA, COMFY_LORA, DIFFUSERS_LORA, ORIGINAL_LORA or LEGACY_LORA.")
print(f"Saving {format_name} to " + OUTPUT)
saver = StableDiffusionXLLoRASaver()
saver.save(model, output_format, OUTPUT, DataType.FLOAT_16.torch_dtype())
print("Done. Size: %d bytes" % os.path.getsize(OUTPUT))
