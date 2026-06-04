import { app } from "electron";
import fs from "fs";
import path from "path";

/** Directory containing the `backend` Python package. */
export function getProjectRoot(): string {
  if (app.isPackaged) {
    return process.resourcesPath;
  }
  return path.resolve(__dirname, "..", "..");
}

export function getBackendDir(): string {
  return path.join(getProjectRoot(), "backend");
}

/** Vite production build served in packaged desktop mode. */
export function getFrontendDistDir(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "frontend", "dist");
  }
  return path.join(getProjectRoot(), "frontend", "dist");
}

export function getUserDataDir(): string {
  const root = app.isPackaged ? app.getPath("userData") : getProjectRoot();
  fs.mkdirSync(root, { recursive: true });
  return root;
}

export function getDataDir(): string {
  const root = path.join(getUserDataDir(), "data");
  fs.mkdirSync(root, { recursive: true });
  return root;
}

export function getCacheDir(): string {
  const root = path.join(getUserDataDir(), "cache");
  fs.mkdirSync(root, { recursive: true });
  return root;
}

export function getTempDir(): string {
  const root = path.join(getUserDataDir(), "tmp");
  fs.mkdirSync(root, { recursive: true });
  return root;
}

/**
 * C-CRIT-01: Path to a bundled, relocatable Python interpreter, if one was
 * shipped with the app (e.g. python-build-standalone under resources/python).
 * Returns null when no bundled runtime is present so callers fall back to the
 * system interpreter. Layout matches python-build-standalone:
 *   Windows: <resources>/python/python.exe
 *   Unix:    <resources>/python/bin/python3
 */
export function getBundledPython(): string | null {
  const base = path.join(getProjectRoot(), "python");
  const candidate =
    process.platform === "win32"
      ? path.join(base, "python.exe")
      : path.join(base, "bin", "python3");
  return fs.existsSync(candidate) ? candidate : null;
}

export function resolvePythonExecutable(): string | null {
  const backendDir = getBackendDir();
  const venvPython =
    process.platform === "win32"
      ? path.join(backendDir, "venv", "Scripts", "python.exe")
      : path.join(backendDir, "venv", "bin", "python");

  // A venv (with deps installed) wins when present.
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }

  // Otherwise prefer a bundled interpreter so the app is self-contained.
  const bundled = getBundledPython();
  if (bundled) {
    return bundled;
  }

  if (process.platform === "win32") {
    return "py";
  }
  return "python3";
}
