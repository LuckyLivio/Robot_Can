"""Download official small Can data with provenance; do not load pickle files."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent


def download(kind):
    dest = ROOT / "data" / f"can_{kind}_v15.hdf5"
    dest.parent.mkdir(parents=True, exist_ok=True)
    name = "low_dim_v15.hdf5" if kind == "ph_lowdim" else "demo_v15.hdf5"
    subset = "ph" if kind.startswith("ph") else "paired"
    url = f"https://huggingface.co/datasets/amandlek/robomimic/resolve/main/v1.5/can/{subset}/{name}"
    if not dest.exists():
        response = requests.get(url, params={"download": "true", "cache_bust": str(int(time.time()))}, stream=True, timeout=(30, 60))
        response.raise_for_status()
        partial = dest.with_suffix(".partial")
        total = 0
        with partial.open("wb") as stream:
            for chunk in response.iter_content(1024 * 1024):
                stream.write(chunk)
                total += len(chunk)
                if total % (10 * 1024 * 1024) < 1024 * 1024:
                    print(f"downloaded {total / 1024**2:.1f} MiB", flush=True)
        partial.replace(dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    manifest = {"kind": kind, "source_url": url, "sha256": digest, "bytes": dest.stat().st_size,
                "downloaded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    dest.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["ph_lowdim", "ph_raw", "paired"], default="ph_lowdim")
    download(parser.parse_args().kind)
