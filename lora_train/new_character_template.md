# New-character LoRA template (clone of fanta-chr002-ressa success, 2026-09-28)

Read this file at the start of every new character job. Two phases, same as Ressa.

## Placeholders (ask user if missing)
- `CHARACTER_FOLDER`: e.g. `fanta-ressa` -> `proj5/<folder>/` (lowercase, dashes)
- `TRIGGER`: underscores only, e.g. `fanta_chr002_ressa` (NEVER hyphens, NEVER in ChatGPT prompts)
- `LORA_FILE`: e.g. `fanta-chr002-ressa.safetensors` (hyphens OK here)
- `REFERENCE_PNG`: full-body character ref the user attaches in chat
- `DESIGN`: one-line identity lock (hair+bow+eyes+outfit+boots+weapon+style). Copy from user's ref description.

## Phase 1 — dataset prompts (after user gives REFERENCE_PNG)
1. Write `lora_train/chatgpt_<folder>_prompts.txt` with 12 V-blocks V01..V12:
   FACE, TORSO, LEGS-SAFE (costume-reference wording, modest stance — bare-thigh
   wording trips ChatGPT policy), BACK, SIDE, GUARD, LUNGE, OVERHEAD, CROUCH,
   WALK, KNEEL, SEATED.
2. Every block = this skeleton, only the last `New pose:` sentence changes:
   `Create a BRAND NEW illustration from scratch, do NOT edit / crop / copy-paste / trace the attached image. Use attached image ONLY for character design identity, ignore its pose, framing and composition completely. Redraw anatomy fully in the new pose described below, with complete head-to-feet body, correct hands and feet, no cut-off limbs, no floating parts. Same character: <DESIGN>, same anime style clean line art. Invent unseen sides consistently in same design language. Do not shift <HAIR-DRIFT-RISK>, do not turn <WEAPON> into <WRONG-WEAPON>, do not change outfit colors. Plain pure white background, full body with margin around feet/head, no other people, no text. New pose: <pose>.`
3. Header must state: attach ref every time, 1 image at a time, keep 8-12 best
   not 30 mediocre, DELETE on drift (wrong hair/weapon/bow/boots/fingers/blur),
   TRIGGER is for OneTrainer captions only, never ChatGPT.
4. User generates images, saves as `proj5/<folder>/1.png .. 12.png` (PNG,
   1024px+, white bg, full body with margin).

## Phase 2 — validate + captions + config (after PNGs land)
1. Validate: 12 PNG exist, each 1024px+, white bg, identity holds
   (hair/bow/outfit/weapon), no duplicates/crops/cut limbs. Report rejects.
2. Write `N.txt` per PNG, format:
   `<TRIGGER>, 1girl, solo, <shot: face closeup|upper body|full body + pose>, <identity constant: hair bow eyes outfit boots weapon>, <image-specific action>, plain white background, anime illustration`
   Rules: TRIGGER first with underscores, keep 1 line, no score_9/pony/artist/
   NSFW tags (training is SFW-clean; NSFW comes at inference via waiNSFW base).
3. OneTrainer config: clone `fanta-ressa/test.json` to `proj5/<folder>/test.json`,
   change ONLY: `base_model_name` (keep waiNSFWIllustrious_v150 unless told),
   `output_model_destination` (new LORA_FILE), concept path/name.
   CRITICAL (2026-09-28 bug): `output_model_format` MUST be `KOHYA_LORA`.
   NEVER `SAFETENSORS` (embedding-only, crashes `trainer.end()` at 100%).
4. Concepts (`training_concepts/test.json` in OneTrainer package): single concept,
   `path` = `C:/Users/steve/opencode/proj5/<folder>`, `type` STANDARD,
   `prompt_source` sample (per-txt), `balancing` 14 REPEATS, 12/12 paired.
   Repeats math: target 1500-2500 steps = images * epochs * repeats
   (12 img x 12 ep x 14 = ~2016, matches Ressa).
   GOTCHA (2026-09-29, cost Saevia a restart): repeats live in the concepts
   file, NOT in test.json. Cloning test.json does NOT carry balancing over —
   it silently resets to 1.0, giving ~5-6 steps/epoch instead of ~84.
   ALWAYS set it by hand for every new character, then verify epoch 1 shows
   ~84 steps before leaving it alone.
5. Known-good train values (keep unless told): SDXL LoRA, res 1024 + bucketing,
   lr 1e-4 cosine w150, batch 2 accum 2, rank 16 alpha 16, bf16 train / float16
   out, grad checkpoint on, Adafactor (fallback AdamW8bit), EMA off,
   backup 30min + before-save, save every epoch, samples null (blind).
6. Hand to user — START-TRAINING CHECKLIST (read back before every Train press):
   a. `Load config` -> `proj5/<folder>/test.json`
   b. Concepts tab: path = `C:/Users/steve/opencode/proj5/<folder>`,
      name = `<folder>`, balancing = **14**, strategy REPEATS
      (verify: NOT 1.0 — see GOTCHA in step 4)
   c. Model tab: `Output Format` = **Kohya** (never Safetensors)
   d. Press Train, watch epoch 1: expect **~84 steps**
      (12 img x 14 repeats / batch 2). If it shows ~5, STOP immediately —
      balancing reset to 1.0, fix per (b) and restart.
   If it ever fails at 100% again, recover with
   `lora_train/convert_backup_to_kohya.sh` (see convert_backup_README.md),
   never retrain.
7. Test: `workflow_sdxl_lora_character_test_api.json` (waiNSFW + LoRA 0.6-1.0,
   832x1248 txt2img, no ControlNet). Pass = identity + weapon + colors hold.
   Only then re-add pose ControlNet.
