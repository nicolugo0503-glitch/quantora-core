// QNT30504 — Strict Live System Client
// Live-first client with strict mode support. Fallback can be disabled from the UI.

window.QNT30501Client = (function () {
  const DEFAULT_POLL_MS = 5000;

  async function safeFetchJson(url, options) {
    try {
      const res = await fetch(url, options || {});
      if (!res.ok) throw new Error("HTTP " + res.status);
      return await res.json();
    } catch (err) {
      return null;
    }
  }

  async function getRuntimeState() {
    return await safeFetchJson("/api/runtime/state")
      || await safeFetchJson("/runtime/state")
      || await safeFetchJson("/api/qnt30501/runtime-state");
  }

  async function getFundState() {
    return await safeFetchJson("/api/funds/summary")
      || await safeFetchJson("/funds/summary")
      || await safeFetchJson("/api/qnt30501/fund-summary");
  }

  async function getInvestors() {
    return await safeFetchJson("/api/investors/overview")
      || await safeFetchJson("/investors/overview")
      || await safeFetchJson("/api/qnt30501/investor-overview");
  }

  async function getExposure() {
    return await safeFetchJson("/api/exposure/summary")
      || await safeFetchJson("/exposure/summary")
      || await safeFetchJson("/api/qnt30501/exposure-summary");
  }

  async function postControl(action) {
    const payload = { action };
    return await safeFetchJson("/api/runtime/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    || await safeFetchJson("/api/qnt30501/runtime-control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  function demoState() {
    return {
      runtime: {
        status: "simulation-fallback",
        cycle_count: 12,
        nav: 734500,
        active_fund: "FUND1",
        last_updated: new Date().toISOString(),
      },
      funds: [
        { sleeve: "Crypto Momentum", capital: 500000 },
        { sleeve: "Low Risk Yield", capital: 300000 },
        { sleeve: "AI Signals", capital: 200000 },
      ],
      investors: [
        { investor: "Nicolas Capital", fund: "FUND1", market_value: 432000, ownership_pct: 60.0 },
        { investor: "Atlas Growth", fund: "FUND1", market_value: 288000, ownership_pct: 40.0 },
      ],
      exposure: { pnl: 23000, source: "demo-fallback" },
    };
  }

  async function loadAll(options) {
    const strictLive = Boolean(options && options.strictLive);
    const [runtime, funds, investors, exposure] = await Promise.all([
      getRuntimeState(), getFundState(), getInvestors(), getExposure()
    ]);

    if (!runtime && !funds && !investors && !exposure) {
      if (strictLive) {
        return {
          runtime: {
            status: "live-endpoints-missing",
            cycle_count: 0,
            nav: 0,
            active_fund: "",
            last_updated: new Date().toISOString(),
          },
          funds: [],
          investors: [],
          exposure: { pnl: 0, source: "strict-live-no-data" },
          strict_error: true,
        };
      }
      return demoState();
    }

    return {
      runtime: runtime || {},
      funds: (funds && (funds.sleeves || funds.rows || funds.data || funds)) || [],
      investors: (investors && (investors.rows || investors.data || investors)) || [],
      exposure: exposure || {},
      strict_error: false,
    };
  }

  return {
    DEFAULT_POLL_MS,
    loadAll,
    postControl,
  };
})();
