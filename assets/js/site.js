(function () {
  const CODE_COLLAPSE_HEIGHT = 300;

  function ready(callback) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", callback, { once: true });
      return;
    }

    callback();
  }

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function initMediumZoom() {
    if (typeof window.mediumZoom !== "function") {
      return;
    }

    window.mediumZoom(".post-content .post-img-view img", {
      margin: 24,
      background: "transparent",
      scrollOffset: 0,
    });
  }

  function initCollapsibleCodeBlocks() {
    document.querySelectorAll(".post-content div.highlight").forEach((block) => {
      if (block.dataset.collapseReady === "true" || block.scrollHeight <= CODE_COLLAPSE_HEIGHT) {
        return;
      }

      block.dataset.collapseReady = "true";
      block.classList.add("is-collapsible", "is-collapsed");

      const controlBar = document.createElement("div");
      controlBar.className = "code-control-bar";

      const button = document.createElement("button");
      button.type = "button";
      button.className = "code-toggle-btn";
      button.setAttribute("aria-expanded", "false");
      button.textContent = "▼ 展开代码";

      controlBar.appendChild(button);
      block.appendChild(controlBar);
      updateExpandedHeight(block);

      button.addEventListener("click", (event) => {
        event.stopPropagation();

        const shouldExpand = block.classList.contains("is-collapsed");
        updateExpandedHeight(block);
        block.classList.toggle("is-collapsed", !shouldExpand);
        block.classList.toggle("is-expanded", shouldExpand);
        controlBar.classList.toggle("is-expanded", shouldExpand);
        button.setAttribute("aria-expanded", String(shouldExpand));
        button.textContent = shouldExpand ? "▲ 收起代码" : "▼ 展开代码";

        if (!shouldExpand) {
          const blockTop = block.getBoundingClientRect().top + window.scrollY;
          if (window.scrollY > blockTop) {
            window.scrollTo({
              top: blockTop - 100,
              behavior: prefersReducedMotion() ? "auto" : "smooth",
            });
          }
        }
      });
    });
  }

  function updateExpandedHeight(block) {
    block.style.setProperty("--code-expanded-height", `${block.scrollHeight + 80}px`);
  }

  function initNotFoundPath() {
    const currentPath = document.getElementById("current-path");
    if (!currentPath) {
      return;
    }

    const path = window.location.pathname;
    currentPath.textContent = path.length > 35 ? `${path.slice(0, 32)}...` : path;
  }

  function initCodeCopyButtons() {
    function enhanceButton(button) {
      if (button.dataset.iconReady === "true") {
        return;
      }

      button.dataset.iconReady = "true";
      button.setAttribute("aria-label", "Copy code");
      button.setAttribute("title", "Copy code");

      button.addEventListener("click", () => {
        button.classList.add("is-copied");
        button.setAttribute("aria-label", "Copied");
        button.setAttribute("title", "Copied");

        window.clearTimeout(button.copyIconTimer);
        button.copyIconTimer = window.setTimeout(() => {
          button.classList.remove("is-copied");
          button.setAttribute("aria-label", "Copy code");
          button.setAttribute("title", "Copy code");
        }, 2000);
      });
    }

    document.querySelectorAll(".copy-code").forEach(enhanceButton);
  }

  function getGiscusTheme() {
    return document.documentElement.dataset.theme === "light" ? "noborder_light" : "noborder_dark";
  }

  function updateGiscusTheme() {
    const theme = getGiscusTheme();
    const giscusScript = document.querySelector('script[src^="https://giscus.app/client.js"]');
    if (giscusScript) {
      giscusScript.setAttribute("data-theme", theme);
    }

    const giscusFrame = document.querySelector("iframe.giscus-frame");
    if (!giscusFrame || !giscusFrame.contentWindow) {
      return;
    }

    giscusFrame.contentWindow.postMessage(
      {
        giscus: {
          setConfig: {
            theme,
          },
        },
      },
      "https://giscus.app"
    );
  }

  function initGiscusThemeSync() {
    const giscusScript = document.querySelector('script[src^="https://giscus.app/client.js"]');
    if (!giscusScript) {
      return;
    }

    updateGiscusTheme();

    const themeObserver = new MutationObserver(updateGiscusTheme);
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    if (document.querySelector("iframe.giscus-frame")) {
      updateGiscusTheme();
      return;
    }

    const frameObserver = new MutationObserver(() => {
      if (!document.querySelector("iframe.giscus-frame")) {
        return;
      }

      updateGiscusTheme();
      frameObserver.disconnect();
    });

    frameObserver.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => frameObserver.disconnect(), 10000);
  }

  ready(function () {
    initMediumZoom();
    initCollapsibleCodeBlocks();
    initNotFoundPath();
    initCodeCopyButtons();
    initGiscusThemeSync();
  });
})();
