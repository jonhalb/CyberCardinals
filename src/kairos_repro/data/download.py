"""Fetch all.tar.gz, VERIFY its SHA-256, and extract only all.tsv.

    python -m kairos_repro.data.download

The checksum comes from the team plan; the first run in Phase 2 either confirms it or
corrects it (and the correction goes in docs/deviations.md). The first URL below was verified on
2026-11-09 (87,860,166 bytes, SHA-256 matches); the first working one wins. Extraction writes the single member named all.tsv
by streaming it, never extractall(), so a hostile archive cannot write elsewhere.
"""
import argparse
import hashlib
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import List, Optional

from kairos_repro.common import DATASET_SHA256, RAW_ARCHIVE, RAW_TSV

CANDIDATE_URLS = [
    "https://raw.githubusercontent.com/sbustreamspot/sbustreamspot-data/master/all.tar.gz",  # verified 2026-11-09
    "https://github.com/sbustreamspot/sbustreamspot-data/raw/master/all.tar.gz",
    "https://github.com/sbustreamspot/sbustreamspot-data/raw/main/all.tar.gz",
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out, 1 << 20)


def extract_all_tsv(archive: Path, out_tsv: Path) -> None:
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if member.isfile() and Path(member.name).name == "all.tsv":
                src = tar.extractfile(member)
                if src is None:
                    continue
                out_tsv.parent.mkdir(parents=True, exist_ok=True)
                with open(out_tsv, "wb") as out:
                    shutil.copyfileobj(src, out, 1 << 20)
                return
    raise FileNotFoundError("no all.tsv inside %s" % archive)


def ensure_dataset(archive: Path = RAW_ARCHIVE, tsv: Path = RAW_TSV,
                   expected_sha: str = DATASET_SHA256, urls: Optional[List[str]] = None) -> str:
    """Download if needed, verify, extract. Returns the verified SHA-256."""
    if not archive.exists():
        last = None
        for url in (urls or CANDIDATE_URLS):
            try:
                print("downloading", url)
                fetch(url, archive)
                last = None
                break
            except Exception as exc:  # try the next candidate
                last = exc
        if last is not None:
            raise RuntimeError("all download URLs failed (last error: %s). "
                               "Download all.tar.gz by hand into data/raw/." % last)
    digest = sha256_of(archive)
    if digest != expected_sha:
        raise ValueError("SHA-256 mismatch for %s\n  expected %s\n  got      %s\n"
                         "Do not proceed. If the dataset host changed the file, record it in docs/deviations.md."
                         % (archive, expected_sha, digest))
    print("sha256 verified:", digest)
    if not tsv.exists():
        extract_all_tsv(archive, tsv)
    print("ready:", tsv)
    return digest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", help="override the download URL (repeatable)")
    ap.add_argument("--sha256", default=DATASET_SHA256)
    a = ap.parse_args()
    ensure_dataset(expected_sha=a.sha256, urls=a.url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
