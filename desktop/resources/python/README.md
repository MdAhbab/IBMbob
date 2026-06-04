# Bundled Python runtime (optional — C-CRIT-01)

This directory is bundled into the packaged app at `resources/python`. When it
contains a real interpreter, the desktop app uses it instead of requiring the
user to have Python installed, making the installer **self-contained**.

By default this folder is empty (only this README + `.gitkeep`), so builds stay
small and the app falls back to the user's system Python.

## To make the installer self-contained

Run, per target platform/arch, before building:

```bash
python packaging/fetch_python.py            # auto-detects host platform/arch
# or explicitly:
python packaging/fetch_python.py --platform mac   --arch arm64
python packaging/fetch_python.py --platform mac   --arch x64
python packaging/fetch_python.py --platform win   --arch x64
python packaging/fetch_python.py --platform linux --arch x64
```

This downloads a relocatable [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
runtime into this folder. Then build normally:

```bash
python packaging/build.py
```

`desktop/src/paths.ts → getBundledPython()` detects the interpreter at
`python/bin/python3` (Unix) or `python/python.exe` (Windows). If absent, the app
falls back to the system interpreter automatically.

> Note: bundling Python adds ~40–80 MB to the installer. Build one installer per
> platform/arch on (or cross-compiling for) that target.
