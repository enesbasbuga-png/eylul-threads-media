#!/usr/bin/env python3
"""Report exactly which source files have not been imported. No publishing."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
photos = json.loads((root / "import_manifest.json").read_text(encoding="utf-8"))["photos"]
missing = [item["source_number"] for item in photos
           if not (root / "images" / item["output_filename"]).is_file()
           or (root / "images" / item["output_filename"]).stat().st_size < 20000]
print(f"IMPORTED: {len(photos)-len(missing)}/{len(photos)}", flush=True)
if missing:
    print(f"MISSING PHOTO NUMBERS: {missing}", file=sys.stderr, flush=True)
    raise SystemExit(1)
print("ALL 129 SOURCE IMAGES ARE PRESENT. Publication remains disabled.")
