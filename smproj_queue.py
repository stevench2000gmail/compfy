#!/usr/bin/env python3
"""Queue ComfyUI jobs from a smproj_extract.py batch txt.

Usage:
  python3 smproj_queue.py batch.txt [--dry-run] [--one jobname]

Each [job:name] queues COUNT images (sequential seeds from SEED, or random
when RANDOMIZE=true). HiresFix-style refine (HIRES=1) runs as a second
low-denoise pass via LatentUpscale, matching the smproj recipe.
Requires: ComfyUI at COMFY_API_URL or http://172.30.240.1:8188
"""
import json
import os
import random
import re
import sys
import urllib.request

API_URL = os.environ.get("COMFY_API_URL", "http://172.30.240.1:8188")
BLOCK_RE = re.compile(r"^(PROMPT|NEGATIVE):\s*$")
KEY_RE = re.compile(r"^[A-Z]+=.*$")
JOB_RE = re.compile(r"^\[job:(.+)\]\s*$")


def parse_batch(path):
    jobs, cur, block = [], None, None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            m = JOB_RE.match(line.strip())
            if m:
                cur = {"name": m.group(1), "PROMPT": "", "NEGATIVE": "", "LORAS": []}
                jobs.append(cur)
                block = None
                continue
            if cur is None:
                continue
            b = BLOCK_RE.match(line.strip())
            if b:
                block = b.group(1)
                continue
            if block and (KEY_RE.match(line.strip()) or JOB_RE.match(line.strip())):
                block = None  # block ended, reprocess this line below
            if block:
                cur[block] += line + "\n"
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k == "LORA" and v:
                    cur["LORAS"].append([v, None])
                elif k == "LORASTRENGTH" and cur["LORAS"] and cur["LORAS"][-1][1] is None:
                    cur["LORAS"][-1][1] = v or "1.0"
                else:
                    cur[k] = v
    for j in jobs:
        j["PROMPT"] = j["PROMPT"].strip()
        j["NEGATIVE"] = j["NEGATIVE"].strip()
    return jobs


def build_workflow(j, positive, negative, seed):
    w, h = j["SIZE"].split("x")
    nodes = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": j["MODEL"]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["2", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {
            "width": int(w), "height": int(h), "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["2", 0], "positive": ["3", 0], "negative": ["4", 0],
            "latent_image": ["5", 0], "seed": seed,
            "steps": int(j["STEPS"]), "cfg": float(j["CFG"]),
            "sampler_name": j["SAMPLER"], "scheduler": j["SCHEDULER"], "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": "PLACEHOLDER", "images": ["7", 0]}},
    }
    # LoRA chain off node 1 (no LoRA => model straight through).
    if j["LORAS"]:
        prev = ["1", 0]
        for i, (fname, wstr) in enumerate(j["LORAS"], start=2):
            s = float(wstr or "1.0")
            nodes[str(i)] = {"class_type": "LoraLoader", "inputs": {
                "lora_name": fname, "strength_model": s, "strength_clip": s,
                "model": prev, "clip": ["1", 1]}}
            prev = [str(i), 0]
        last_lora = str(1 + len(j["LORAS"]))
        nodes["3"]["inputs"]["clip"] = [last_lora, 1]
        nodes["6"]["inputs"]["model"] = [last_lora, 0]
    else:
        # No LoRA: model straight through, no loader node.
        nodes["3"]["inputs"]["clip"] = ["1", 1]
        nodes["6"]["inputs"]["model"] = ["1", 0]
    if int(j.get("HIRES", 0)):
        sc = float(j.get("HSCALE", 2))
        nodes["9"] = {"class_type": "LatentUpscale", "inputs": {
            "samples": ["6", 0], "upscale_method": "nearest-exact", "crop": "disabled",
            "width": int(int(w) * sc), "height": int(int(h) * sc)}}
        nodes["10"] = {"class_type": "KSampler", "inputs": {
            "model": nodes["6"]["inputs"]["model"], "positive": ["3", 0], "negative": ["4", 0],
            "latent_image": ["9", 0], "seed": seed + 1,
            "steps": int(j.get("HSTEPS", 40)), "cfg": float(j.get("HCFG", 7.0)),
            "sampler_name": j["SAMPLER"], "scheduler": j["SCHEDULER"],
            "denoise": float(j.get("HDENOISE", 0.6))}}
        nodes["7"]["inputs"]["samples"] = ["10", 0]
    return nodes


def queue(workflow):
    data = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(f"{API_URL}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()[:120]


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        sys.exit("usage: smproj_queue.py batch.txt [--dry-run] [--one jobname]")
    jobs = parse_batch(sys.argv[1])
    only, dry = None, "--dry-run" in sys.argv
    if "--one" in sys.argv:
        only = sys.argv[sys.argv.index("--one") + 1]
        jobs = [j for j in jobs if only in j["name"]]
        if not jobs:
            sys.exit(f"no job matches '{only}'")
    n = 0
    for j in jobs:
        count = int(j.get("COUNT", 1))
        rand = j.get("RANDOMIZE", "true") == "true"
        try:
            base_seed = int(j.get("SEED", "0"))
        except ValueError:
            base_seed, rand = 0, True
        for v in range(count):
            seed = random.randint(0, 2**31 - 1) if rand else base_seed + v
            wf = build_workflow(j, j["PROMPT"], j["NEGATIVE"], seed)
            wf["8"]["inputs"]["filename_prefix"] = f"{j.get('PREFIX', 'proj5_' + j['name'])}"
            if dry:
                print(f"[{j['name']} {v + 1}/{count} seed={seed}] {j['PROMPT'][:100]}...")
            else:
                queue(wf)
                print(f"queued {j['name']} {v + 1}/{count} seed={seed}")
            n += 1
    print(f"{'DRY-RUN ' if dry else ''}done: {n} image(s)")


if __name__ == "__main__":
    main()
