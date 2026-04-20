// QNT30493 — Browser state adapter
// Additive only. No core files modified.

export function loadQuantoraOperatorState() {
  const raw = localStorage.getItem("quantora_qnt30493_state");
  return raw ? JSON.parse(raw) : null;
}

export function saveQuantoraOperatorState(state) {
  localStorage.setItem("quantora_qnt30493_state", JSON.stringify(state));
  return state;
}

export function getRuntimeSummary() {
  const state = loadQuantoraOperatorState();
  if (!state) return null;
  return {
    status: state.runtime?.status || "idle",
    activeFund: state.runtime?.activeFund || "",
    cycleCount: state.runtime?.cycleCount || 0,
    nav: state.runtime?.navSnapshot?.nav || 0,
    totalPnl: state.runtime?.totalPnl || 0,
  };
}
