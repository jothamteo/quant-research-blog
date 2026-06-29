"""Capybara cover generator (ComfyUI + SDXL, local on the Mac mini).

Evolved house style: the same calm storybook capybara at a cozy trading desk, but
each cover now carries the *specific* quant motif of its post plus more charts,
financial symbols and statistical notation — consistent mascot, informative art.

Usage:
    python make_cover_capybara.py <slug> [seed]
The motif/prompt for <slug> is looked up in MOTIFS below. Renders 1344x768 on the
local ComfyUI server (127.0.0.1:8188, sd_xl_base_1.0), centre-crops to the blog's
1200x630 banner, and writes static/covers/<slug>.png.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
COVERS = ROOT / "static" / "covers"
COMFY = "http://127.0.0.1:8188"
COMFY_OUT = Path.home() / "Desktop" / "lumora-prints" / "comfyui" / "output"
CKPT = "sd_xl_base_1.0.safetensors"

# shared style so every capybara reads as the same character / world
STYLE = ("children's storybook illustration, soft Studio Ghibli style, a calm cute "
         "capybara sitting at a cozy wooden desk working at a glowing computer "
         "monitor, warm pastel palette, cream and sage-green tones, potted plants, "
         "soft warm window light, hand-drawn, gentle, wholesome, highly aesthetic, "
         "flat soft shading, ")
NEG = ("photo, realistic, 3d render, harsh, dark, scary, horror, gore, text, "
       "watermark, signature, ugly, deformed, extra limbs, lowres, glitch, noisy, "
       "oversaturated, neon, jpeg artifacts")

# per-post motif: what is ON the screen / floating around the capybara
MOTIFS = {
    "fx-transient-impact":
        ("the monitor shows a sharp price spike that then decays back down (a line "
         "that jumps up then mean-reverts), surrounded by floating line charts, "
         "candlestick charts, currency symbols dollar euro yen, and small "
         "mathematical and statistical notation, foreign-exchange trading theme"),
    "llm-forecaster-profit":
        ("the capybara is gazing into a glowing crystal ball on the desk, inside "
         "the crystal ball floats probability numbers and a tiny prediction market "
         "price chart, scattered around the desk are bar charts, accuracy graphs, "
         "floating yes/no binary cards, small brain and dollar coin icons, soft "
         "magical forecasting glow, cozy bookshelf in background, whimsical quant theme"),
    "amm-oracle-manipulation":
        ("the monitor shows a hyperbolic constant-product curve x*y=k with a dot "
         "sliding along it, surrounded by floating liquidity pool icons, DeFi token "
         "symbols, oracle eye symbols, a small hacker figure pushing a balance scale, "
         "blockchain hexagon patterns in background, cozy crypto quant theme"),
    "hyperliquid-risk-engine":
        ("the computer monitor on the desk clearly shows a crypto candlestick price "
         "chart that crashes downward, a few small green up-candles on the left then "
         "one big dramatic long red candlestick plunging straight down at the right, "
         "a steep market crash dump, a small red downward arrow, simple clean "
         "hand-drawn candlesticks painted in the same soft storybook style as the "
         "scene, a few small floating red percentage-down and dollar symbols, "
         "tense market-crash mood but still cozy and warm"),
}


def build_workflow(prompt: str, neg: str, seed: int, w: int = 1344, h: int = 768):
    """Minimal SDXL txt2img graph in ComfyUI API format."""
    return {
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": CKPT}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": neg, "clip": ["4", 1]}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": w, "height": h, "batch_size": 1}},
        "3": {"class_type": "KSampler",
              "inputs": {"seed": seed, "steps": 32, "cfg": 7.0,
                         "sampler_name": "dpmpp_2m", "scheduler": "karras",
                         "denoise": 1.0, "model": ["4", 0],
                         "positive": ["6", 0], "negative": ["7", 0],
                         "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"filename_prefix": "capy_cover", "images": ["8", 0]}},
    }


def submit(workflow: dict) -> str:
    body = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(f"{COMFY}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]


def wait_for(prompt_id: str, timeout: int = 300) -> dict:
    """Poll history until the prompt finishes; return the output image ref dict."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with urllib.request.urlopen(f"{COMFY}/history/{prompt_id}") as r:
            hist = json.loads(r.read())
        if prompt_id in hist:
            outs = hist[prompt_id]["outputs"]
            for node in outs.values():
                for img in node.get("images", []):
                    return img
        time.sleep(2)
    raise TimeoutError("ComfyUI render timed out")


def fetch_image(ref: dict, dst: Path):
    """Download the rendered image over the ComfyUI /view API (path-agnostic)."""
    q = urllib.parse.urlencode({"filename": ref["filename"],
                                "subfolder": ref.get("subfolder", ""),
                                "type": ref.get("type", "output")})
    with urllib.request.urlopen(f"{COMFY}/view?{q}") as r:
        dst.write_bytes(r.read())


def crop_to_banner(src: Path, dst: Path, tw: int = 1200, th: int = 630):
    """Centre-crop to the 1200x630 aspect, then resize."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    target = tw / th
    if w / h > target:                       # too wide -> crop sides
        nw = int(h * target); x0 = (w - nw) // 2
        im = im.crop((x0, 0, x0 + nw, h))
    else:                                    # too tall -> crop top/bottom
        nh = int(w / target); y0 = (h - nh) // 2
        im = im.crop((0, y0, w, y0 + nh))
    im.resize((tw, th), Image.LANCZOS).save(dst)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in MOTIFS:
        sys.exit(f"usage: make_cover_capybara.py <slug>  (known: {list(MOTIFS)})")
    slug = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 77
    prompt = STYLE + MOTIFS[slug]
    print(f"[{slug}] seed={seed} submitting...")
    pid = submit(build_workflow(prompt, NEG, seed))
    ref = wait_for(pid)
    raw = Path(tempfile.gettempdir()) / ref["filename"]
    fetch_image(ref, raw)
    print(f"[{slug}] rendered {ref['filename']} -> cropping to banner")
    dst = COVERS / f"{slug}.png"
    crop_to_banner(raw, dst)
    print(f"[{slug}] wrote {dst}")


if __name__ == "__main__":
    main()
