// Irin: "WiFi setup" link on the status page, placed just above OTA Update.
//
// Context-sensitive: shown only while the captive portal is running (the device is
// on its fallback AP). The portal answers /config.json; on the home network nothing
// does, so the fetch fails and the link stays hidden. Any path the status page
// doesn't claim gets the portal's setup page, so /wifi is just a readable one.
(async () => {
  try {
    const r = await fetch("/config.json", { cache: "no-store" });
    if (!r.ok || !("aps" in (await r.json()))) return;
  } catch {
    return;
  }

  await customElements.whenDefined("esp-app");
  const root = document.querySelector("esp-app")?.shadowRoot;
  if (!root) return;

  const place = () => {
    if (root.getElementById("irin-wifi")) return;
    const ota = [...root.querySelectorAll(".tab-header")].find(
      (h) => h.textContent.trim() === "OTA Update"
    );
    if (!ota) return;
    const box = document.createElement("div");
    box.id = "irin-wifi";
    box.innerHTML =
      '<div class="tab-header">WiFi Setup</div>' +
      '<div class="tab-container"><a class="btn" href="/wifi">' +
      "Change WiFi network or password</a></div>";
    ota.before(box);
  };
  // The page renders its sections after the first state stream arrives, and a
  // re-render can drop foreign nodes, so keep watching.
  new MutationObserver(place).observe(root, { childList: true, subtree: true });
  place();
})();
