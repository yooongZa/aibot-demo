// Chainlit Copilot widget loader. Reads server URL from <meta name="chainlit-server"> if present,
// otherwise defaults to http://localhost:8000.
//
// Adds an opaque backdrop behind the widget so landing-page content does not
// bleed through the chat window, and locks body scroll while the widget is open.
(function () {
  const meta = document.querySelector('meta[name="chainlit-server"]');
  window.CHAINLIT_SERVER =
    (meta && meta.content) ||
    window.CHAINLIT_SERVER ||
    "http://localhost:8000";

  let backdrop = null;
  let isOpen = false;

  function ensureBackdrop() {
    if (backdrop) return backdrop;
    backdrop = document.createElement("div");
    backdrop.className = "copilot-backdrop";
    backdrop.addEventListener("click", closeCopilot);
    document.body.appendChild(backdrop);
    return backdrop;
  }

  function openBackdrop() {
    ensureBackdrop().classList.add("open");
    document.body.classList.add("copilot-open");
    isOpen = true;
  }

  function closeBackdrop() {
    if (backdrop) backdrop.classList.remove("open");
    document.body.classList.remove("copilot-open");
    isOpen = false;
  }

  function toggleWidget() {
    if (typeof window.toggleChainlitCopilot === "function") {
      window.toggleChainlitCopilot();
      if (isOpen) {
        closeBackdrop();
      } else {
        openBackdrop();
      }
    } else {
      window.open(window.CHAINLIT_SERVER, "_blank");
    }
  }

  function closeCopilot() {
    if (!isOpen) return;
    if (typeof window.toggleChainlitCopilot === "function") {
      window.toggleChainlitCopilot();
    }
    closeBackdrop();
  }

  window.openCopilot = toggleWidget;
  window.closeCopilot = closeCopilot;

  // ESC closes the widget
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && isOpen) closeCopilot();
  });

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
      " \u2014 fallback: clicking the CTA opens the chat in a new tab."
    );
  };
  document.body.appendChild(script);
})();
