#!/usr/bin/env python3
"""Manually triggered import of archived Eylul photos; no Threads publishing."""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import gdown
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "import_manifest.json"
DEST = ROOT / "images"


def convert_image(source: Path, dest: Path) -> None:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        if image.mode not in ("RGB", "L"):
            if image.mode in ("RGBA", "LA") or ("transparency" in image.info):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
        if image.mode == "L":
            image = image.convert("RGB")
        if min(image.size) < 500:
            raise ValueError(f"Image too small: {image.size}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, "JPEG", quality=92, optimize=True, progressive=True, subsampling=0)
        with Image.open(dest) as verify:
            verify.verify()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--continue-on-error", action="store_true",
                        help="Save successful imports even if some Drive files fail")
    args = parser.parse_args()
    if args.start < 1 or args.count < 1 or args.count > 50:
        parser.error("start must be positive, count must be 1..50")

    all_items = json.loads(MANIFEST.read_text(encoding="utf-8"))["photos"]
    items = [item for item in all_items
             if args.start <= item["source_number"] < args.start + args.count]
    if not items:
        parser.error("No images in requested range")
    DEST.mkdir(exist_ok=True)
    succeeded, skipped, failed = [], [], []
    for item in items:
        no = item["source_number"]
        dest = DEST / item["output_filename"]
        if dest.exists() and dest.stat().st_size > 20_000:
            print(f"SKIP {no:03d}: already imported",flush=True)
            skipped.append(no)
            continue
        print(f"IMPORT {no:03d} -> {dest.name}",flush=True)
        success = False
        for attempt in range(1, 4):
            with tempfile.TemporaryDirectory(prefix="eylul-import-") as folder:
                temp = Path(folder) / "input.png"
                try:
                    received = gdown.download(
                        id=item["drive_id"], output=str(temp), quiet=True,
                        use_cookies=False)
                    if not received or not temp.exists() or temp.stat().st_size < 20_000:
                        raise RuntimeError("Drive download incomplete or unavailable")
                    convert_image(temp, dest)
                    print(f"OK {no:03d}: {dest.stat().st_size:,} bytes",flush=True)
                    succeeded.append(no)
                    success = True
                    break
                except (Exception) as e:
                    if dest.exists():
                        dest.unlink()
                    print(f"WARNING {no:03d} attempt {attempt}: {e}",file=sys.stderr,flush=True)
                    if attempt < 3:
                        time.sleep(attempt * 12)
        if not success:
            failed.append(no)
            print(f"ERROR {no:03d}: all attempts failed; moving to next image",
                  file=sys.stderr, flush=True)
        time.sleep(5)
    print(json.dumps({"imported":succeeded,"skipped":skipped,"failed":failed}))
    if failed and not args.continue_on_error:
        raise SystemExit("Import incomplete: please rerun this range")
    if failed:
        print(f"WARNING: failed image numbers in this batch: {failed}",
              file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
