// QNT30496 - Command Center Button Integration
// Additive only. No core files modified.
//
// Usage:
// 1) Load this file in the browser console or append as a script.
// 2) It will inject mission buttons into the current Quantora command center DOM.
// 3) Buttons open mission assets in a new tab when possible.

(function () {
  const MANIFEST_PATH = "MISSIONS/QNT30496_COMMAND_CENTER_BUTTON_INTEGRATION/mission_button_manifest.json";

  function guessBasePath() {
    const href = window.location.href;
    if (href.includes("/index.html")) return href.split("/index.html")[0] + "/";
    return href.endsWith("/") ? href : href + "/";
  }

  function createButton(meta) {
    const btn = document.createElement("button");
    btn.textContent = meta.label;
    btn.title = meta.mission_code + " — " + meta.title;
    btn.style.background = "#2455d6";
    btn.style.border = "1px solid #3f6fff";
    btn.style.color = "#fff";
    btn.style.borderRadius = "8px";
    btn.style.padding = "8px 12px";
    btn.style.fontSize = "12px";
    btn.style.cursor = "pointer";
    btn.style.whiteSpace = "nowrap";
    btn.onclick = function () {
      const base = guessBasePath();
      const target = base + meta.relative_path;
      window.open(target, "_blank");
    };
    return btn;
  }

  function makeSection(manifest) {
    const wrapper = document.createElement("section");
    wrapper.id = "qnt30496-mission-button-hub";
    wrapper.style.marginTop = "14px";
    wrapper.style.padding = "12px";
    wrapper.style.border = "1px solid rgba(70,110,255,0.35)";
    wrapper.style.borderRadius = "12px";
    wrapper.style.background = "rgba(20,36,74,0.35)";

    const title = document.createElement("div");
    title.textContent = "Conversation Missions Hub";
    title.style.color = "#dbe7ff";
    title.style.fontWeight = "700";
    title.style.fontSize = "14px";
    title.style.marginBottom = "10px";

    const subtitle = document.createElement("div");
    subtitle.textContent = "QNT30484–QNT30495 quick-launch buttons added without modifying core UI files.";
    subtitle.style.color = "#9bb0ce";
    subtitle.style.fontSize = "12px";
    subtitle.style.marginBottom = "10px";

    const grid = document.createElement("div");
    grid.style.display = "flex";
    grid.style.flexWrap = "wrap";
    grid.style.gap = "8px";

    manifest.buttons.forEach(meta => grid.appendChild(createButton(meta)));

    wrapper.appendChild(title);
    wrapper.appendChild(subtitle);
    wrapper.appendChild(grid);
    return wrapper;
  }

  function inject(manifest) {
    if (document.getElementById("qnt30496-mission-button-hub")) return;

    const candidates = Array.from(document.querySelectorAll("body *")).filter(el => {
      const text = (el.textContent || "").trim();
      return text.includes("Added Missions Hub") || text.includes("Mission Directory") || text.includes("Launch Panel");
    });

    const anchor = candidates[0] || document.body;
    const section = makeSection(manifest);

    if (anchor === document.body) {
      document.body.appendChild(section);
    } else {
      anchor.parentNode.insertBefore(section, anchor.nextSibling);
    }
  }

  fetch(MANIFEST_PATH)
    .then(r => r.json())
    .then(manifest => inject(manifest))
    .catch(err => {
      console.error("QNT30496 injection failed:", err);
      alert("QNT30496 could not load mission_button_manifest.json. Open the standalone mission hub instead.");
    });
})();
