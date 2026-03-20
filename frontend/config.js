(function () {
  const host = window.location.host;
  const localHosts = ["127.0.0.1:8010", "localhost:8010", "127.0.0.1:5173", "localhost:5173", "[::1]:5173"];
  const isLocal = localHosts.includes(host) || host.startsWith("127.0.0.1:") || host.startsWith("localhost:");
  window.API_BASE_URL = isLocal ? "http://127.0.0.1:8010" : window.location.origin;
})();
