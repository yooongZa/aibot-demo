// Chainlit Copilot widget loader. Reads server URL from <meta name="chainlit-server"> if present,
// otherwise defaults to http://localhost:8000.
//
// CTA buttons ('상담 시작' etc.) open the chat in a new tab, which is the
// most reliable cross-browser behaviour — the inline widget button stays
// available at the bottom-right for users who prefer an overlay.
(function () {
  const meta = document.querySelector('meta[name="chainlit-server"]');
  window.CHAINLIT_SERVER =
    (meta && meta.content) ||
    window.CHAINLIT_SERVER ||
    "http://localhost:8000";

  window.openCopilot = function () {
    window.open(window.CHAINLIT_SERVER, "_blank", "noopener,noreferrer");
  };

  const script = document.createElement("script");
  script.src = window.CHAINLIT_SERVER + "/copilot/index.js";
  script.async = true;
  script.onload = function () {
    if (typeof window.mountChainlitWidget === "function") {
      window.mountChainlitWidget({
        chainlitServer: window.CHAINLIT_SERVER,
        theme: "light",
        button: { style: { bgcolor: "#16a34a", color: "#ffffff" } },
      });
    }
  };
  script.onerror = function () {
    console.warn(
      "[copilot] Chainlit server not reachable at " + window.CHAINLIT_SERVER +
      " \u2014 CTA will still open the chat URL in a new tab."
    );
  };
  document.body.appendChild(script);
})();
