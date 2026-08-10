/** Waits for the Google Identity Services script (loaded via a static
 * `<script async defer>` tag in index.html) to finish loading, since GSI
 * ships no npm package we could import/await directly. Safe to call more
 * than once — resolves immediately if the script already finished. */
let loadPromise: Promise<void> | null = null;

export function loadGoogleIdentityScript(): Promise<void> {
  if (window.google) {
    return Promise.resolve();
  }
  if (loadPromise) {
    return loadPromise;
  }

  loadPromise = new Promise((resolve, reject) => {
    const script = document.getElementById("google-identity-script");
    if (!script) {
      reject(new Error("Google Identity Services script tag not found in index.html"));
      return;
    }
    script.addEventListener("load", () => resolve(), { once: true });
    script.addEventListener(
      "error",
      () => reject(new Error("Failed to load Google Identity Services script")),
      { once: true },
    );
  });
  return loadPromise;
}
