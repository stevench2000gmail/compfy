#!/usr/bin/env bash
# Convert a OneTrainer INTERNAL backup dir to a loadable LoRA file.
# Must use OneTrainer's own venv python (has torch/safetensors/diffusers).
# Usage:
#   ./convert_backup_to_kohya.sh [backup_dir_or_file] [output.safetensors] [KOHYA_LORA|COMFY_LORA|DIFFUSERS_LORA|ORIGINAL_LORA|LEGACY_LORA]
# Defaults reproduce the 2026-09-28 fanta-chr002-ressa recovery.
set -e

OT_ROOT_WIN='C:\Users\steve\Downloads\StabilityMatrix-win-x64\Data\Packages\OneTrainer'
OT_ROOT_WSL='/mnt/c/Users/steve/Downloads/StabilityMatrix-win-x64/Data/Packages/OneTrainer'
VENV_PYTHON_WIN='C:\Users\steve\Downloads\StabilityMatrix-win-x64\Data\Packages\OneTrainer\venv\Scripts\python.exe'
VENV_PYTHON_WSL='/mnt/c/Users/steve/Downloads/StabilityMatrix-win-x64/Data/Packages/OneTrainer/venv/Scripts/python.exe'
SCRIPT_WIN='C:\Users\steve\opencode\proj5\lora_train\convert_backup_to_kohya.py'
DEFAULT_BACKUP_WIN='C:\Users\steve\Downloads\StabilityMatrix-win-x64\Data\Packages\OneTrainer\workspace\run\backup\2026-09-28_11-56-33-backup-1008-12-0'
DEFAULT_OUTPUT_WIN='C:\Users\steve\Downloads\StabilityMatrix-win-x64\Data\Models\Lora\fanta-chr002-ressa.safetensors'

to_win_path() {
    local p="$1"
    if command -v wslpath >/dev/null 2>&1 && [[ "$p" == /mnt/* ]]; then
        wslpath -w "$p"
    else
        printf '%s' "$p"
    fi
}

BACKUP_IN="${1:-$DEFAULT_BACKUP_WIN}"
OUTPUT_IN="${2:-$DEFAULT_OUTPUT_WIN}"
FORMAT="${3:-KOHYA_LORA}"

BACKUP_WIN="$(to_win_path "$BACKUP_IN")"
OUTPUT_WIN="$(to_win_path "$OUTPUT_IN")"

if [[ ! -x "$VENV_PYTHON_WSL" ]]; then
    echo "ERROR: venv python not found at $VENV_PYTHON_WSL" >&2
    echo "Is StabilityMatrix installed at the expected path?" >&2
    exit 1
fi

cd "$OT_ROOT_WSL"
exec "$VENV_PYTHON_WSL" -X utf8 "$SCRIPT_WIN" "$BACKUP_WIN" "$OUTPUT_WIN" "$FORMAT"
