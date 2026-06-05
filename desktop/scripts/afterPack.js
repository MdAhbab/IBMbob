/**
 * afterPack hook — ad-hoc deep-sign the macOS .app so the bundle signature
 * properly seals all bundled resources (Python runtime, backend, migrations).
 *
 * Apple Silicon requires every binary to be signed; electron-builder only
 * applies a partial "linker-signed" signature when real code signing is
 * skipped (no Developer ID). That partial signature leaves the bundle
 * incompletely sealed, which can cause Gatekeeper to report the downloaded
 * app as "damaged". A free ad-hoc deep sign (`codesign -s -`) re-seals the
 * whole bundle so users only see the milder "unidentified developer" prompt
 * that right-click → Open bypasses — no $99 Developer ID required.
 */
const { execSync } = require("child_process");
const path = require("path");

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== "darwin") return;

  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(context.appOutDir, `${appName}.app`);

  try {
    execSync(`codesign --deep --force --timestamp=none -s - "${appPath}"`, {
      stdio: "inherit",
    });
    execSync(`codesign --verify --deep --strict "${appPath}"`, {
      stdio: "inherit",
    });
    console.log(`[afterPack] ad-hoc deep-signed: ${appPath}`);
  } catch (err) {
    console.warn(`[afterPack] ad-hoc sign failed (non-fatal): ${err.message}`);
  }
};
