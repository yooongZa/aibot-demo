// Chainlit Copilot widget loader. Reads server URL from <meta name="chainlit-server"> if present,
// otherwise defaults to http://localhost:8000.
(function () {
  const meta = document.querySelector('meta[name="chainlit-server"]');
  window.CHAINLIT_SERVER =
    (meta && meta.content) ||
    window.CHAINLIT_SERVER ||
    "http://localhost:8000";

  window.openCopilot = function () {
    if (typeof window.toggleChainlitCopilot === "function") {
      window.toggleChainlitCopilot();
    } else {
      window.open(window.CHAINLIT_SERVER, "_blank");
    }
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
      window.toggleChainlitCopilot = function () {
        window.dispatchEvent(new CustomEvent("chainlit-copilot-toggle"));
      };
    }
  };
  script.onerror = function () {
    console.warn(
      "[copilot] Chainlit server not reachable at " + window.CHAINLIT_SERVER +
      " — fallback: clicking the CTA opens the chat in a new tab."
    );
  };
  document.body.appendChild(script);
})();
