#!/usr/bin/env python3
"""Extract one or more Stability Matrix .smproj files into a single batch txt.

Usage:
  python3 smproj_extract.py [-o batch.txt] job1.smproj [job2.smproj ...]

Output is a single human-editable txt: one [job:name] section per smproj
(MODEL/SAMPLER/SIZE/HIRES/PROMPT/NEGATIVE/SEED/COUNT/...). Then queue with:
  python3 smproj_queue.py batch.txt [--dry-run] [--one jobname]

Notes:
- <lora:file:weight> tags are pulled out of Prompt into LORA=/LORASTRENGTH=
  lines (ComfyUI needs real LoraLoader nodes, not prompt tags).
- Prompt line-breaks are preserved. Inside PROMPT:/NEGATIVE: blocks, avoid
  starting a line with ALL-CAPS= or [job: (parser limitation, documented).
"""
import json
import os
import re
import sys

LORA_RE = re.compile(r"<lora:([^:>]+):([0-9.]+)>")


def mod_by_type(modules, want):
    try:
        for m in modules.get("$values", []):
            if m.get("$type") == want:
                return m
    except (AttributeError, TypeError):
        pass
    return None


def inner_vals(mod):
    vals = (mod or {}).get("$values", [])
    return vals if isinstance(vals, list) else []


def find_sampler(modules):
    for m in modules if isinstance(modules, list) else []:
        if isinstance(m, dict) and m.get("$type") == "Sampler":
            return m
    return None


def extract(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    state = data.get("State", {})
    name = os.path.splitext(os.path.basename(path))[0]

    model = state.get("Model", {})
    sampler = state.get("Sampler", {})
    prompt = state.get("Prompt", {})
    batch = state.get("BatchSize", {})
    seed = state.get("Seed", {})

    # HiresFix lives in State.Modules.$values[] as HiresFixModule.
    hires_mod = mod_by_type(state.get("Modules", {}), "HiresFixModule")
    hires_on = bool((hires_mod or {}).get("IsEnabled", False))
    hscale, hsteps, hcfg, hdenoise = 2, 40, 7.0, 0.6
    if hires_mod:
        for v in inner_vals(hires_mod):
            if isinstance(v, dict) and v.get("$type") == "Upscaler":
                try:
                    hscale = int(v.get("Scale", hscale))
                except (TypeError, ValueError):
                    pass
        hs = find_sampler(inner_vals(hires_mod))
        if hs:
            hsteps = hs.get("Steps", hsteps)
            hcfg = hs.get("CfgScale", hcfg)
            hdenoise = hs.get("DenoiseStrength", hdenoise)

    raw_prompt = (prompt.get("Prompt") or "").replace("\r\n", "\n")
    raw_neg = (prompt.get("NegativePrompt") or "").replace("\r\n", "\n")

    loras = LORA_RE.findall(raw_prompt) + LORA_RE.findall(raw_neg)
    clean_prompt = LORA_RE.sub("", raw_prompt)
    clean_prompt = re.sub(r"\n{3,}", "\n\n", clean_prompt).strip()
    clean_neg = LORA_RE.sub("", raw_neg).strip()

    # Dedupe LoRAs, keep first weight seen.
    seen, lora_lines = set(), []
    for fname, w in loras:
        if not fname.endswith(".safetensors"):
            fname += ".safetensors"  # smproj stores LoRA names extensionless; ComfyUI needs the file
        if fname not in seen:
            seen.add(fname)
            lora_lines.append((fname, w))

    out = [f"[job:{name}]", f"SOURCE={path}"]
    out.append(f"MODEL={model.get('SelectedModelName', '')}")
    vae = model.get("SelectedVaeName") or "@default"
    out.append(f"VAE={vae}")
    if lora_lines:
        for fname, w in lora_lines:
            out.append(f"LORA={fname}")
            out.append(f"LORASTRENGTH={w}")
    else:
        out.append("LORA=")
    out.append(f"SAMPLER={(sampler.get('SelectedSampler') or {}).get('Name', 'euler_ancestral')}")
    out.append(f"SCHEDULER={(sampler.get('SelectedScheduler') or {}).get('Name', 'normal')}")
    out.append(f"STEPS={sampler.get('Steps', 30)}")
    out.append(f"CFG={sampler.get('CfgScale', 4.5)}")
    out.append(f"SIZE={sampler.get('Width', 640)}x{sampler.get('Height', 768)}")
    out.append(f"HIRES={1 if hires_on else 0}")
    out.append(f"HSCALE={hscale}")
    out.append(f"HSTEPS={hsteps}")
    out.append(f"HCFG={hcfg}")
    out.append(f"HDENOISE={hdenoise}")
    out.append(f"SEED={seed.get('Seed', '0')}")
    out.append(f"RANDOMIZE={str(bool(seed.get('IsRandomizeEnabled', True))).lower()}")
    out.append(f"COUNT={int(batch.get('BatchCount', 1)) * int(batch.get('BatchSize', 1))}")
    out.append(f"PREFIX=proj5_{name}")
    out.append("PROMPT:")
    out.append(clean_prompt)
    out.append("NEGATIVE:")
    out.append(clean_neg)
    out.append("")
    return "\n".join(out)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-o")]
    outfile = None
    if "-o" in sys.argv:
        i = sys.argv.index("-o")
        if i + 1 >= len(sys.argv) or not sys.argv[i + 1].endswith(".txt"):
            sys.exit("usage: smproj_extract.py [-o batch.txt] job1.smproj [job2.smproj ...]")
        outfile = sys.argv[i + 1]
        args = [a for a in args if a != outfile]
    if not args or not all(a.endswith(".smproj") for a in args):
        sys.exit("usage: smproj_extract.py [-o batch.txt] job1.smproj [job2.smproj ...]")
    header = ("# batch config from smproj_extract.py — edit freely, then:\n"
              "#   python3 smproj_queue.py batch.txt [--dry-run] [--one jobname]\n")
    body = "\n".join(extract(p) for p in args)
    text = header + body
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {outfile} ({len(args)} job(s))")
    else:
        print(text)


if __name__ == "__main__":
    main()
