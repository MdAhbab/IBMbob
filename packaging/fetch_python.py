"""
fetch_python.py — download a relocatable Python runtime for self-contained builds.
(Addresses audit finding C-CRIT-01: installer is not self-contained.)

Downloads a `python-build-standalone` "install_only" runtime and extracts it into
`desktop/resources/python/` so electron-builder bundles it. The desktop app
(`desktop/src/paths.ts → getBundledPython()`) then uses it instead of requiring the
end user to have Python installed.

Usage:
  python packaging/fetch_python.py                       # auto-detect host
  python packaging/fetch_python.py --platform mac --arch arm64
  python packaging/fetch_python.py --platform win --arch x64
  python packaging/fetch_python.py --platform linux --arch x64
  python packaging/fetch_python.py --clean               # remove bundled runtime

Notes:
  * Run once per platform/arch you intend to ship (build on/for that target).
  * The runtime is git-ignored; only the folder + README are committed.
  * Bump PBS_RELEASE / PY_VERSION to update the bundled interpreter.
"""

from __future__ import annotations

import argparse
import io
import platform
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

# Pinned python-build-standalone release + CPython version. Bump as needed.
# Releases: https://github.com/astral-sh/python-build-standalone/releases
PBS_RELEASE = "20240814"
PY_VERSION = "3.12.5"

BASE_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/"
    f"{PBS_RELEASE}"
)

# (platform, arch) -> target triple used in the asset filename
TRIPLES = {
    ("mac", "arm64"): "aarch64-apple-darwin",
    ("mac", "x64"): "x86_64-apple-darwin",
    ("win", "x64"): "x86_64-pc-windows-msvc",
    ("linux", "x64"): "x86_64-unknown-linux-gnu",
    ("linux", "arm64"): "aarch64-unknown-linux-gnu",
}

DEST = Path(__file__).resolve().parent.parent / "desktop" / "resources" / "python"


def detect_host() -> tuple[str, str]:
    sysname = platform.system().lower()
    plat = {"darwin": "mac", "windows": "win", "linux": "linux"}.get(sysname, sysname)
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    return plat, arch


def asset_name(triple: str) -> str:
    # The "install_only" archive extracts to a top-level `python/` directory.
    return f"cpython-{PY_VERSION}+{PBS_RELEASE}-{triple}-install_only.tar.gz"


def clean() -> None:
    if not DEST.exists():
        print(f"Nothing to clean at {DEST}")
        return
    for child in DEST.iterdir():
        if child.name in (".gitkeep", "README.md"):
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    print(f"Cleaned bundled runtime from {DEST}")


def fetch(plat: str, arch: str) -> int:
    triple = TRIPLES.get((plat, arch))
    if not triple:
        print(f"ERROR: unsupported platform/arch: {plat}/{arch}")
        print(f"Supported: {sorted(TRIPLES.keys())}")
        return 1

    url = f"{BASE_URL}/{asset_name(triple)}"
    print(f"Downloading {url}")
    try:
        with urllib.request.urlopen(url) as resp:  # noqa: S310 (trusted GitHub URL)
            data = resp.read()
    except Exception as exc:  # pragma: no cover - network
        print(f"ERROR: download failed: {exc}")
        print("Check PBS_RELEASE / PY_VERSION or your network and retry.")
        return 1

    # Reset destination (keep README + .gitkeep)
    clean()
    DEST.mkdir(parents=True, exist_ok=True)

    print("Extracting…")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tmp = DEST / "_extract"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir()
        tar.extractall(tmp)  # noqa: S202 (trusted archive)
        # Archive top-level is `python/`; move its contents up into DEST.
        inner = tmp / "python"
        src = inner if inner.is_dir() else tmp
        for item in src.iterdir():
            target = DEST / item.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            shutil.move(str(item), str(target))
        shutil.rmtree(tmp)

    # Sanity-check the resulting interpreter path.
    interp = (
        DEST / "python.exe" if plat == "win" else DEST / "bin" / "python3"
    )
    if interp.exists():
        print(f"OK — bundled interpreter at {interp}")
        return 0
    print(f"WARNING: expected interpreter not found at {interp}; inspect {DEST}")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Download a relocatable Python for bundling.")
    ap.add_argument("--platform", choices=["mac", "win", "linux"])
    ap.add_argument("--arch", choices=["x64", "arm64"])
    ap.add_argument("--clean", action="store_true", help="Remove the bundled runtime and exit.")
    args = ap.parse_args()

    if args.clean:
        clean()
        return 0

    host_plat, host_arch = detect_host()
    plat = args.platform or host_plat
    arch = args.arch or host_arch
    print(f"Target: {plat}/{arch}  (CPython {PY_VERSION}, PBS {PBS_RELEASE})")
    return fetch(plat, arch)


if __name__ == "__main__":
    sys.exit(main())
