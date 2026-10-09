#!/usr/bin/env python3
"""Download the 1,432 reference SVG logos into assets/library/svg/.

The logos are trademarks of their owners (see TRADEMARKS.md), so this repository
does not commit them. This script fetches them on demand from the upstream
skill repository at a pinned commit and checks the whole set against a pinned
SHA-256 manifest before installing it. Standard library only.

Usage:
  python3 scripts/fetch_library.py           # no-op if already installed
  python3 scripts/fetch_library.py --force   # re-download
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request

UPSTREAM = "kaankiziltug/logo-design-skill"
COMMIT = "0ecf52e9a4b3ac92b714f7cc6e3148ab8c774134"  # v1.4.4
RAW_URL = ("https://raw.githubusercontent.com/" + UPSTREAM + "/" + COMMIT
           + "/skills/logo-design/assets/library/svg/{name}")
#: sha256 of the sorted "name\0sha256(content)\n" lines of all 1,432 files.
MANIFEST_SHA256 = "e16580c332ed745b8d4d55e9de06a9825461a33923a27b63cd93a219346f1e61"

MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 30_000_000
WORKERS = 8
TIMEOUT = 30
NAME_RE = re.compile(r"[A-Za-z0-9._-]+\.svg")

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBRARY_DIR = os.path.join(SKILL_DIR, "assets", "library")
SVG_DIR = os.path.join(LIBRARY_DIR, "svg")
CATALOG_PATH = os.path.join(LIBRARY_DIR, "catalog.json")


def catalog_names():
    with open(CATALOG_PATH, encoding="utf-8") as fh:
        names = [row["file"] for row in json.load(fh)]
    bad = [n for n in names if not NAME_RE.fullmatch(n)]
    if bad:
        sys.exit(f"Unexpected file names in catalog.json: {bad[:3]}")
    return sorted(set(names))


def manifest_of(directory, names):
    digest = hashlib.sha256()
    for name in names:
        with open(os.path.join(directory, name), "rb") as fh:
            file_hash = hashlib.sha256(fh.read()).hexdigest()
        digest.update(name.encode() + b"\0" + file_hash.encode() + b"\n")
    return digest.hexdigest()


def is_installed(names):
    if not all(os.path.isfile(os.path.join(SVG_DIR, n)) for n in names):
        return False
    return manifest_of(SVG_DIR, names) == MANIFEST_SHA256


def download(name, dest_dir):
    url = RAW_URL.format(name=urllib.parse.quote(name))
    request = urllib.request.Request(url, headers={"User-Agent": "logo-design-skill-fetch"})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                data = response.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ValueError("file too large")
            if b"<svg" not in data[:4096]:
                raise ValueError("not an SVG")
            with open(os.path.join(dest_dir, name), "wb") as fh:
                fh.write(data)
            return len(data)
        except Exception as exc:  # retried, then reported
            last_error = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"{name}: {last_error}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args()

    names = catalog_names()
    if not args.force and is_installed(names):
        print(f"Library already installed: {len(names)} SVGs in {SVG_DIR}")
        return

    tmp_dir = tempfile.mkdtemp(prefix="svg-download-", dir=LIBRARY_DIR)
    try:
        print(f"Downloading {len(names)} reference SVGs from {UPSTREAM}@{COMMIT[:7]}…")
        total = 0
        errors = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futures = {pool.submit(download, n, tmp_dir): n for n in names}
            for future in concurrent.futures.as_completed(futures):
                try:
                    total += future.result()
                except Exception as exc:
                    errors.append(str(exc))
                if total > MAX_TOTAL_BYTES:
                    for pending in futures:
                        pending.cancel()
                    sys.exit("Aborted: download larger than expected.")
        if errors:
            sys.exit(f"{len(errors)} file(s) failed, nothing installed. First: {errors[0]}")
        if manifest_of(tmp_dir, names) != MANIFEST_SHA256:
            sys.exit("Integrity check failed (content differs from the pinned commit); nothing installed.")
        if os.path.isdir(SVG_DIR):
            shutil.rmtree(SVG_DIR)
        os.replace(tmp_dir, SVG_DIR)
        print(f"Installed {len(names)} SVGs ({total / 1e6:.1f} MB) in {SVG_DIR}")
    finally:
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
