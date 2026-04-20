// QNT30497 — Native Command Center Integration Registry
// Additive only. No existing core files are modified.
//
// Purpose:
// Provide a production-ready registry of mission buttons that can be mounted
// natively inside the Quantora command center.

export const QNT30497_MISSION_BUTTONS = [
  { id: "qnt30484", label: "Fund Stack", missionCode: "QNT30484", href: "MISSIONS/QNT30484_FUND_STACK_SLEEVE_SYSTEM/README.md" },
  { id: "qnt30485", label: "Investor Ledger", missionCode: "QNT30485", href: "MISSIONS/QNT30485_INVESTOR_LEDGER/README.md" },
  { id: "qnt30486", label: "Fund NAV", missionCode: "QNT30486", href: "MISSIONS/QNT30486_FUND_NAV_ENGINE/README.md" },
  { id: "qnt30487", label: "Investor Dashboard", missionCode: "QNT30487", href: "MISSIONS/QNT30487_INVESTOR_DASHBOARD/README.md" },
  { id: "qnt30488", label: "Monetization", missionCode: "QNT30488", href: "MISSIONS/QNT30488_MONETIZATION_ENGINE/README.md" },
  { id: "qnt30489", label: "System Integration", missionCode: "QNT30489", href: "MISSIONS/QNT30489_SYSTEM_INTEGRATION_LAYER/README.md" },
  { id: "qnt30490", label: "Live Bridge", missionCode: "QNT30490", href: "MISSIONS/QNT30490_LIVE_DATA_EXECUTION_BRIDGE/README.md" },
  { id: "qnt30491", label: "Activation Runtime", missionCode: "QNT30491", href: "MISSIONS/QNT30491_SYSTEM_ACTIVATION_LAYER/README.md" },
  { id: "qnt30492", label: "Control Panel UI", missionCode: "QNT30492", href: "MISSIONS/QNT30492_CONTROL_PANEL_UI/control_panel.html" },
  { id: "qnt30493", label: "Real Control Panel", missionCode: "QNT30493", href: "MISSIONS/QNT30493_REAL_CONTROL_PANEL_WIRED/real_control_panel.html" },
  { id: "qnt30494", label: "Exec Fund Bridge", missionCode: "QNT30494", href: "MISSIONS/QNT30494_EXECUTION_FUND_INTEGRATION_BRIDGE/README.md" },
  { id: "qnt30495", label: "Fund Visualization", missionCode: "QNT30495", href: "MISSIONS/QNT30495_LIVE_FUND_VISUALIZATION/fund_visualization.html" },
];

export function getQNT30497Buttons() {
  return QNT30497_MISSION_BUTTONS.slice();
}
