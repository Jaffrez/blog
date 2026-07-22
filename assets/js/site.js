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

  function initCopyrightDetails() {
    document.querySelectorAll(".copy-details").forEach((container) => {
      const control = container.querySelector(":scope > .copy-summary");
      const content = container.querySelector(":scope > .copy-content");
      if (!control || !content) {
        return;
      }

      let isAnimating = false;
      let animationTimer;

      function clearAnimationStyles() {
        content.style.removeProperty("transition");
        content.style.removeProperty("height");
        content.style.removeProperty("overflow");
      }

      control.addEventListener("click", () => {
        if (isAnimating) {
          return;
        }

        const isClosing = control.getAttribute("aria-expanded") === "true";
        if (prefersReducedMotion()) {
          control.setAttribute("aria-expanded", String(!isClosing));
          content.hidden = isClosing;
          clearAnimationStyles();
          return;
        }

        isAnimating = true;

        function finishAnimation() {
          window.clearTimeout(animationTimer);
          if (isClosing) {
            content.hidden = true;
          }
          clearAnimationStyles();
          isAnimating = false;
        }

        content.style.overflow = "hidden";
        content.style.transition = "height 180ms ease";

        let expandedHeight;

        if (isClosing) {
          content.style.height = `${content.getBoundingClientRect().height}px`;
          control.setAttribute("aria-expanded", "false");
        } else {
          content.hidden = false;
          content.style.height = "auto";
          expandedHeight = content.getBoundingClientRect().height;
          content.style.height = "0px";
          control.setAttribute("aria-expanded", "true");
        }

        content.getBoundingClientRect();
        animationTimer = window.setTimeout(finishAnimation, 190);

        window.requestAnimationFrame(() => {
          content.style.height = isClosing ? "0px" : `${expandedHeight}px`;
        });
      });
    });
  }

  function initTableOfContents() {
    document.querySelectorAll("details.toc").forEach((details) => {
      const summary = details.querySelector(":scope > summary");
      const content = details.querySelector(":scope > .inner");
      if (!summary || !content) {
        return;
      }

      let contentInner = content.querySelector(":scope > .toc-content-inner");
      if (!contentInner) {
        contentInner = document.createElement("div");
        contentInner.className = "toc-content-inner";
        while (content.firstChild) {
          contentInner.appendChild(content.firstChild);
        }
        content.appendChild(contentInner);
      }

      contentInner.querySelectorAll("li").forEach((item) => {
        const hasDirectLink = item.querySelector(":scope > a");
        const hasNestedList = item.querySelector(":scope > ul");
        item.classList.toggle("toc-branch", Boolean(hasNestedList && !hasDirectLink));
      });

      let isAnimating = false;
      let animationTimer;

      function clearAnimationStyles() {
        content.style.removeProperty("transition");
        content.style.removeProperty("height");
        content.style.removeProperty("overflow");
      }

      summary.addEventListener(
        "click",
        (event) => {
          event.preventDefault();
          if (isAnimating) {
            return;
          }

          const isClosing = details.open;
          if (prefersReducedMotion()) {
            details.open = !isClosing;
            clearAnimationStyles();
            return;
          }

          isAnimating = true;
          let expandedHeight;

          function finishAnimation() {
            window.clearTimeout(animationTimer);
            if (isClosing) {
              details.open = false;
            }
            clearAnimationStyles();
            isAnimating = false;
          }

          content.style.overflow = "hidden";
          content.style.transition = "height 180ms ease";

          if (isClosing) {
            content.style.height = `${content.getBoundingClientRect().height}px`;
          } else {
            content.style.height = "auto";
            expandedHeight = content.getBoundingClientRect().height;
            content.style.height = "0px";
            details.open = true;
          }

          content.getBoundingClientRect();
          animationTimer = window.setTimeout(finishAnimation, 190);

          window.requestAnimationFrame(() => {
            content.style.height = isClosing ? "0px" : `${expandedHeight}px`;
          });
        },
        true
      );
    });
  }

  function getGiscusTheme() {
    return document.documentElement.dataset.theme === "light" ? "noborder_light" : "noborder_dark";
  }

  function getGiscusOrigin(loader) {
    try {
      return new URL(loader.dataset.scriptUrl, window.location.href).origin;
    } catch (_error) {
      return "https://giscus.app";
    }
  }

  function updateGiscusTheme() {
    const theme = getGiscusTheme();

    document.querySelectorAll(".giscus-loader").forEach((loader) => {
      const script = loader.querySelector("script[data-giscus-script]");
      if (script) {
        script.setAttribute("data-theme", theme);
      }

      const frame = loader.querySelector("iframe.giscus-frame");
      if (!frame || !frame.contentWindow) {
        return;
      }

      frame.contentWindow.postMessage(
        {
          giscus: {
            setConfig: {
              theme,
            },
          },
        },
        getGiscusOrigin(loader)
      );
    });
  }

  function watchForGiscusFrame(loader) {
    if (loader.querySelector("iframe.giscus-frame")) {
      updateGiscusTheme();
      return;
    }

    const frameObserver = new MutationObserver(() => {
      if (!loader.querySelector("iframe.giscus-frame")) {
        return;
      }

      updateGiscusTheme();
      frameObserver.disconnect();
    });

    frameObserver.observe(loader, { childList: true, subtree: true });
    window.setTimeout(() => frameObserver.disconnect(), 15000);
  }

  function loadGiscus(loader) {
    if (loader.dataset.state === "loading" || loader.dataset.state === "loaded") {
      return;
    }

    const status = loader.querySelector(".giscus-status");
    const retry = loader.querySelector(".giscus-retry");
    if (!status || !retry || !loader.dataset.scriptUrl) {
      return;
    }

    loader.querySelectorAll("script[data-giscus-script], .giscus").forEach((element) => element.remove());
    loader.dataset.state = "loading";
    status.hidden = false;
    status.textContent = "评论加载中…";
    retry.hidden = true;

    const script = document.createElement("script");
    const attributes = [
      ["repo", "data-repo"],
      ["repoId", "data-repo-id"],
      ["category", "data-category"],
      ["categoryId", "data-category-id"],
      ["mapping", "data-mapping"],
      ["strict", "data-strict"],
      ["reactionsEnabled", "data-reactions-enabled"],
      ["emitMetadata", "data-emit-metadata"],
      ["inputPosition", "data-input-position"],
      ["lang", "data-lang"],
    ];

    script.src = loader.dataset.scriptUrl;
    script.async = true;
    script.crossOrigin = "anonymous";
    script.dataset.giscusScript = "true";
    script.setAttribute("data-theme", getGiscusTheme());

    attributes.forEach(([property, attribute]) => {
      if (loader.dataset[property]) {
        script.setAttribute(attribute, loader.dataset[property]);
      }
    });

    script.addEventListener(
      "load",
      () => {
        loader.dataset.state = "loaded";
        status.hidden = true;
        retry.hidden = true;
        watchForGiscusFrame(loader);
      },
      { once: true }
    );

    script.addEventListener(
      "error",
      () => {
        script.remove();
        loader.dataset.state = "error";
        status.hidden = false;
        status.textContent = "评论加载失败，请稍后重试。";
        retry.hidden = false;
      },
      { once: true }
    );

    loader.appendChild(script);
  }

  function initGiscusLazyLoad() {
    document.querySelectorAll(".giscus-loader").forEach((loader) => {
      const retry = loader.querySelector(".giscus-retry");
      if (retry) {
        retry.addEventListener("click", () => loadGiscus(loader));
      }

      if (!("IntersectionObserver" in window)) {
        loadGiscus(loader);
        return;
      }

      const observer = new IntersectionObserver(
        (entries) => {
          if (!entries.some((entry) => entry.isIntersecting)) {
            return;
          }

          observer.disconnect();
          loadGiscus(loader);
        },
        { rootMargin: "600px 0px" }
      );

      observer.observe(loader);
    });
  }

  function initGiscusThemeSync() {
    if (!document.querySelector(".giscus-loader")) {
      return;
    }

    const themeObserver = new MutationObserver(updateGiscusTheme);
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
  }

  ready(function () {
    initMediumZoom();
    initCollapsibleCodeBlocks();
    initNotFoundPath();
    initCodeCopyButtons();
    initCopyrightDetails();
    initTableOfContents();
    initGiscusLazyLoad();
    initGiscusThemeSync();
  });
})();
