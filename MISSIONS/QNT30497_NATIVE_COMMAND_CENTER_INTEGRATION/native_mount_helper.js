// QNT30497 — Native Mount Helper
// Additive only. No existing core files are modified.

import { getQNT30497Buttons } from "./mission_button_registry.js";

export function mountQNT30497MissionButtons(targetElement, options = {}) {
  if (!targetElement) {
    throw new Error("mountQNT30497MissionButtons requires a targetElement");
  }

  const title = options.title || "Conversation Missions";
  const subtitle = options.subtitle || "QNT30484–QNT30495";

  const section = document.createElement("section");
  section.className = "qnt30497-native-mission-section";
  section.style.border = "1px solid rgba(70,110,255,0.35)";
  section.style.borderRadius = "12px";
  section.style.padding = "12px";
  section.style.background = "rgba(20,36,74,0.35)";
  section.style.marginTop = "12px";

  const header = document.createElement("div");
  header.style.marginBottom = "10px";

  const titleEl = document.createElement("div");
  titleEl.textContent = title;
  titleEl.style.color = "#dbe7ff";
  titleEl.style.fontWeight = "700";
  titleEl.style.fontSize = "14px";

  const subEl = document.createElement("div");
  subEl.textContent = subtitle;
  subEl.style.color = "#9bb0ce";
  subEl.style.fontSize = "12px";
  subEl.style.marginTop = "4px";

  header.appendChild(titleEl);
  header.appendChild(subEl);

  const grid = document.createElement("div");
  grid.style.display = "flex";
  grid.style.flexWrap = "wrap";
  grid.style.gap = "8px";

  getQNT30497Buttons().forEach(meta => {
    const btn = document.createElement("button");
    btn.textContent = meta.label;
    btn.dataset.missionCode = meta.missionCode;
    btn.title = meta.missionCode;
    btn.style.background = "#2455d6";
    btn.style.border = "1px solid #3f6fff";
    btn.style.color = "#fff";
    btn.style.borderRadius = "8px";
    btn.style.padding = "8px 12px";
    btn.style.fontSize = "12px";
    btn.style.cursor = "pointer";
    btn.onclick = () => {
      const base = options.basePath || "";
      const href = base ? base.replace(/\/$/, "") + "/" + meta.href : meta.href;
      if (options.onOpen) {
        options.onOpen(meta, href);
      } else {
        window.open(href, "_blank");
      }
    };
    grid.appendChild(btn);
  });

  section.appendChild(header);
  section.appendChild(grid);
  targetElement.appendChild(section);
  return section;
}
