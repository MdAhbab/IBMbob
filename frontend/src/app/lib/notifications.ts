let audioCtx: AudioContext | null = null;

function playChime() {
  try {
    audioCtx ??= new AudioContext();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.frequency.value = 880;
    gain.gain.value = 0.04;
    osc.start();
    osc.stop(audioCtx.currentTime + 0.12);
  } catch {
    /* ignore */
  }
}

export function notifyUser(
  title: string,
  body: string,
  prefs: { sound?: boolean; desktopNotifs?: boolean },
) {
  if (prefs.sound) playChime();
  if (
    prefs.desktopNotifs &&
    typeof Notification !== "undefined" &&
    Notification.permission === "granted"
  ) {
    try {
      new Notification(title, { body, tag: "orchestrator" });
    } catch {
      /* ignore */
    }
  }
}
