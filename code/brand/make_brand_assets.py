"""Capybara brand-asset generator (ComfyUI + SDXL, local on the Mac mini).

Same calm storybook capybara as the post covers, rendered as the two standing
brand assets:
  - profile : square avatar, capybara head/shoulders at the desk, clean bg
  - banner  : wide X/Twitter header (3:1), capybara at a multi-monitor quant desk
              with charts + statistical notation, room for handle text on the side

Usage:
    python3 make_brand_assets.py profile [seed]
    python3 make_brand_assets.py banner  [seed]

Outputs:
    static/brand/profile.png   (1000x1000)
    static/brand/banner.png    (1500x500)
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
BRAND = ROOT / "static" / "brand"
COMFY = "http://127.0.0.1:8188"
CKPT = "sd_xl_base_1.0.safetensors"

# shared style so the brand capybara reads as the same character as the covers
STYLE = ("children's storybook illustration, soft Studio Ghibli style, a calm cute "
         "capybara working at a cozy wooden trading desk, warm pastel palette, cream "
         "and sage-green tones, potted plants, soft warm window light, hand-drawn, "
         "gentle, wholesome, highly aesthetic, flat soft shading, ")
NEG = ("photo, realistic, 3d render, harsh, dark, scary, horror, gore, text, "
       "watermark, signature, ugly, deformed, extra limbs, lowres, glitch, noisy, "
       "oversaturated, neon, jpeg artifacts")

ASSETS = {
    # square avatar: tight on the capybara, simple readable background
    "profile": {
        "motif": ("close-up portrait of the capybara, head and shoulders, sitting "
                  "at the desk with a single glowing monitor behind showing a small "
                  "line chart, simple soft background, centered, friendly, looking "
                  "at the viewer"),
        "render": (1024, 1024),
        "out": (1000, 1000),
    },
    # wide header: full desk scene, charts + notation, empty-ish left for handle text
    "banner": {
        "motif": ("wide panoramic view of the capybara at a multi-monitor quant "
                  "trading desk, the monitors show line charts, candlestick charts "
                  "and a volatility smile, floating mathematical and statistical "
                  "notation and currency symbols around the screens, calm and cozy, "
                  "the capybara on the right side, open soft sky-and-plant background "
                  "on the left with empty space"),
        "render": (1536, 512),
        "out": (1500, 500),
    },
}


def build_workflow(prompt: str, neg: str, seed: int, w: int, h: int):
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
              "inputs": {"filename_prefix": "capy_brand", "images": ["8", 0]}},
    }


def submit(workflow: dict) -> str:
    body = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(f"{COMFY}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]


def wait_for(prompt_id: str, timeout: int = 300) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with urllib.request.urlopen(f"{COMFY}/history/{prompt_id}") as r:
            hist = json.loads(r.read())
        if prompt_id in hist:
            for node in hist[prompt_id]["outputs"].values():
                for img in node.get("images", []):
                    return img
        time.sleep(2)
    raise TimeoutError("ComfyUI render timed out")


def fetch_image(ref: dict, dst: Path):
    q = urllib.parse.urlencode({"filename": ref["filename"],
                                "subfolder": ref.get("subfolder", ""),
                                "type": ref.get("type", "output")})
    with urllib.request.urlopen(f"{COMFY}/view?{q}") as r:
        dst.write_bytes(r.read())


def crop_resize(src: Path, dst: Path, tw: int, th: int):
    """Centre-crop to target aspect, then resize."""
    im = Image.open(src).convert("RGB")
    w, h = im.size
    target = tw / th
    if w / h > target:
        nw = int(h * target); x0 = (w - nw) // 2
        im = im.crop((x0, 0, x0 + nw, h))
    else:
        nh = int(w / target); y0 = (h - nh) // 2
        im = im.crop((0, y0, w, y0 + nh))
    im.resize((tw, th), Image.LANCZOS).save(dst)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ASSETS:
        sys.exit(f"usage: make_brand_assets.py <asset>  (known: {list(ASSETS)})")
    key = sys.argv[1]
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 77
    spec = ASSETS[key]
    prompt = STYLE + spec["motif"]
    rw, rh = spec["render"]
    print(f"[{key}] seed={seed} submitting {rw}x{rh}...")
    pid = submit(build_workflow(prompt, NEG, seed, rw, rh))
    ref = wait_for(pid)
    raw = Path(tempfile.gettempdir()) / ref["filename"]
    fetch_image(ref, raw)
    BRAND.mkdir(parents=True, exist_ok=True)
    tw, th = spec["out"]
    dst = BRAND / f"{key}.png"
    crop_resize(raw, dst, tw, th)
    print(f"[{key}] wrote {dst} ({tw}x{th})")


if __name__ == "__main__":
    main()
