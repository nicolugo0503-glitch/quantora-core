// QNT30519B — Dynamic Mission Registry Loader Fix
window.QNT30519MissionRegistry = (function () {
  async function loadManifest() {
    const res = await fetch("mission_registry.json", { cache: "no-store" });
    if (!res.ok) throw new Error("Unable to load mission_registry.json");
    return await res.json();
  }

  function createButton(meta) {
    const btn = document.createElement("button");
    btn.className = "secondary qnt30519-dynamic-button";
    btn.textContent = meta.label;
    btn.dataset.missionCode = meta.code;
    btn.onclick = () => { window.location.href = meta.path; };
    return btn;
  }

  function createCard(meta) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="code">${meta.code}</div>
      <div class="title">${meta.label}</div>
      <div class="notes">Auto-registered mission route from the dynamic registry system.</div>
      <div class="actions"><a class="btn" href="${meta.path}">Open</a></div>
    `;
    return card;
  }

  function findButtonAnchor() {
    const buttons = Array.from(document.querySelectorAll("button"));
    return buttons.find(btn => (btn.textContent || "").trim() === "Conversation Missions");
  }

  function ensureDynamicSection(anchorBtn) {
    let section = document.getElementById("qnt30519-dynamic-section");
    if (section) return section;

    section = document.createElement("div");
    section.id = "qnt30519-dynamic-section";
    section.style.display = "flex";
    section.style.flexWrap = "wrap";
    section.style.gap = "8px";
    section.style.marginTop = "8px";

    if (anchorBtn && anchorBtn.parentNode) {
      anchorBtn.parentNode.insertBefore(section, anchorBtn.nextSibling);
    } else {
      document.body.appendChild(section);
    }
    return section;
  }

  async function mountButtons(containerSelector) {
    const manifest = await loadManifest();
    let container = containerSelector ? document.querySelector(containerSelector) : null;
    const anchorBtn = findButtonAnchor();

    if (!container) {
      container = ensureDynamicSection(anchorBtn);
    }

    const existingCodes = new Set(
      Array.from(document.querySelectorAll("[data-mission-code]")).map(x => x.dataset.missionCode)
    );

    manifest.missions.forEach(meta => {
      if (!existingCodes.has(meta.code)) {
        const btn = createButton(meta);
        container.appendChild(btn);
      }
    });

    return { ok:true, count: manifest.missions.length };
  }

  async function mountCards(containerSelector) {
    const manifest = await loadManifest();
    const container = document.querySelector(containerSelector);
    if (!container) return { ok:false, error:"card container not found" };

    const existingCodes = new Set(Array.from(container.querySelectorAll(".code")).map(x => (x.textContent || "").trim()));
    manifest.missions.forEach(meta => {
      if (!existingCodes.has(meta.code)) {
        container.appendChild(createCard(meta));
      }
    });
    return { ok:true, count: manifest.missions.length };
  }

  return { loadManifest, mountButtons, mountCards };
})();
