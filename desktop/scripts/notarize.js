/**
 * electron-builder afterSign hook — macOS notarization (C-CRIT-02).
 *
 * This runs automatically after the .app is code-signed. It is a no-op unless
 * the required Apple credentials are present in the environment, so unsigned
 * local/dev builds keep working with zero configuration.
 *
 * To enable notarization, export before building `npm run dist:mac`:
 *   APPLE_ID                  = your Apple ID email
 *   APPLE_APP_SPECIFIC_PASSWORD = an app-specific password (appleid.apple.com)
 *   APPLE_TEAM_ID             = your 10-char Apple Developer Team ID
 *
 * Code signing itself is driven by electron-builder when a Developer ID
 * certificate is available (via the macOS keychain, or CSC_LINK/CSC_KEY_PASSWORD).
 */
const path = require("path");

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;

  if (electronPlatformName !== "darwin") {
    return; // only macOS is notarized
  }

  const appleId = process.env.APPLE_ID;
  const applePassword = process.env.APPLE_APP_SPECIFIC_PASSWORD;
  const teamId = process.env.APPLE_TEAM_ID;

  if (!appleId || !applePassword || !teamId) {
    console.log(
      "[notarize] Skipped — APPLE_ID / APPLE_APP_SPECIFIC_PASSWORD / APPLE_TEAM_ID not set. " +
        "Build is unsigned/un-notarized (fine for local testing)."
    );
    return;
  }

  let notarize;
  try {
    ({ notarize } = require("@electron/notarize"));
  } catch (err) {
    console.warn(
      "[notarize] @electron/notarize not installed — skipping. Run `npm i -D @electron/notarize`."
    );
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = path.join(appOutDir, `${appName}.app`);

  console.log(`[notarize] Notarizing ${appPath} (team ${teamId})…`);
  await notarize({
    appPath,
    appleId,
    appleIdPassword: applePassword,
    teamId,
  });
  console.log("[notarize] Done.");
};
