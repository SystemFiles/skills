/* sykesdev-design-system — Harbor Chart behavior layer.
 *
 * Declarative: every behavior is opted into with a data attribute, so a
 * document only pays for what it marks up. No dependencies, no build step,
 * no network — the file survives being inlined into a single-file document
 * and opened from file://.
 *
 *   [data-tabs]                 tablist with arrow-key roving focus
 *   [data-sort-table]           click / Enter on a th button to sort
 *   [data-filter="tableId"]     text input that filters that table's rows
 *   [data-copy="targetId"]      copy the target's text, confirm in a toast
 *   [data-dialog="dialogId"]    open a <dialog>; [data-close] closes it
 *   [data-toast="message"]      raise a toast on click
 *   [data-toc="selector"]       build a rail from headings, with scrollspy
 *   [data-anchors="selector"]   add # handles to those headings
 *   [data-sample]               broadcast dataset to [data-sample-slot] nodes
 *   [data-favicon] on an <img>  reuse that image as the tab icon
 */

(() => {
  "use strict";

  const all = (selector, root = document) => [...root.querySelectorAll(selector)];

  /* ------------------------------------------------------------- toasts */

  function toastStack() {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      stack.setAttribute("role", "status");
      stack.setAttribute("aria-live", "polite");
      document.body.append(stack);
    }
    return stack;
  }

  function toast(message, ms = 3200) {
    const node = document.createElement("div");
    node.className = "toast";
    node.textContent = message;
    toastStack().append(node);
    window.setTimeout(() => node.remove(), ms);
  }

  /* --------------------------------------------------------------- tabs */

  function initTabs(root) {
    const tabs = all('[role="tab"]', root);
    const select = (tab) => {
      tabs.forEach((other) => {
        const selected = other === tab;
        other.setAttribute("aria-selected", String(selected));
        other.tabIndex = selected ? 0 : -1;
        const panel = document.getElementById(other.getAttribute("aria-controls"));
        if (panel) panel.hidden = !selected;
      });
    };

    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => select(tab));
      tab.addEventListener("keydown", (event) => {
        const step = { ArrowRight: 1, ArrowLeft: -1, Home: -index, End: tabs.length }[
          event.key
        ];
        if (step === undefined) return;
        event.preventDefault();
        const next = tabs[(index + step + tabs.length) % tabs.length];
        next.focus();
        select(next);
      });
    });

    select(tabs.find((tab) => tab.getAttribute("aria-selected") === "true") || tabs[0]);
  }

  /* -------------------------------------------------------------- table */

  // Numeric-looking cells sort numerically; everything else sorts as text.
  function cellKey(row, index) {
    const text = (row.cells[index]?.textContent || "").trim();
    const numeric = Number(text.replace(/[,\s%$]/g, ""));
    return Number.isFinite(numeric) && text !== "" ? numeric : text.toLowerCase();
  }

  function initSortTable(table) {
    const headers = all("thead th", table);
    headers.forEach((th, index) => {
      if (th.dataset.noSort !== undefined) return;
      const label = th.textContent.trim();
      th.setAttribute("aria-sort", "none");
      th.innerHTML = "";
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      th.append(button);

      button.addEventListener("click", () => {
        const ascending = th.getAttribute("aria-sort") !== "ascending";
        headers.forEach((other) => other.setAttribute("aria-sort", "none"));
        th.setAttribute("aria-sort", ascending ? "ascending" : "descending");

        const body = table.tBodies[0];
        [...body.rows]
          .sort((a, b) => {
            const left = cellKey(a, index);
            const right = cellKey(b, index);
            if (left === right) return 0;
            return (left < right ? -1 : 1) * (ascending ? 1 : -1);
          })
          .forEach((row) => body.append(row));
      });
    });
  }

  function initFilter(input) {
    const table = document.getElementById(input.dataset.filter);
    if (!table) return;
    const status = document.getElementById(input.dataset.filterStatus || "");
    input.addEventListener("input", () => {
      const needle = input.value.trim().toLowerCase();
      let shown = 0;
      [...table.tBodies[0].rows].forEach((row) => {
        const hit = row.textContent.toLowerCase().includes(needle);
        row.hidden = !hit;
        if (hit) shown += 1;
      });
      if (status) status.textContent = `${shown} of ${table.tBodies[0].rows.length}`;
    });
  }

  /* ---------------------------------------------------- copy and dialogs */

  function initCopy(button) {
    const target = document.getElementById(button.dataset.copy);
    if (!target) return;
    button.addEventListener("click", async () => {
      const text = (target.textContent || "").trim();
      try {
        await navigator.clipboard.writeText(text);
        toast("Copied to clipboard");
      } catch {
        // file:// and insecure origins deny the clipboard; select instead so
        // the reader can still copy by hand.
        const range = document.createRange();
        range.selectNodeContents(target);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        toast("Clipboard blocked — text selected, press copy");
      }
    });
  }

  function initDialogTrigger(button) {
    const dialog = document.getElementById(button.dataset.dialog);
    if (!dialog) return;
    button.addEventListener("click", () => dialog.showModal());
    all("[data-close]", dialog).forEach((close) =>
      close.addEventListener("click", () => dialog.close(close.dataset.close || "")),
    );
  }

  /* -------------------------------------------------------- doc furniture */

  function slug(text) {
    return text
      .toLowerCase()
      .replace(/[^\w\s-]/g, "")
      .trim()
      .replace(/\s+/g, "-");
  }

  // The heading's own words, without any anchor handle already appended to it,
  // so a TOC reads the same whichever ran first.
  function headingText(heading) {
    return [...heading.childNodes]
      .filter((node) => !(node.nodeType === 1 && node.classList.contains("anchor")))
      .map((node) => node.textContent)
      .join("")
      .trim();
  }

  function initAnchors(host) {
    all(host.dataset.anchors).forEach((heading) => {
      const text = headingText(heading);
      heading.id ||= slug(text);
      const link = document.createElement("a");
      link.className = "anchor";
      link.href = `#${heading.id}`;
      link.textContent = "#";
      link.setAttribute("aria-label", `Link to ${text}`);
      heading.append(link);
    });
  }

  function initToc(host) {
    const headings = all(host.dataset.toc).filter((heading) => {
      heading.id ||= slug(headingText(heading));
      return heading.id;
    });
    if (!headings.length) return;

    const list = document.createElement("ol");
    const links = headings.map((heading) => {
      const item = document.createElement("li");
      const link = document.createElement("a");
      link.href = `#${heading.id}`;
      link.textContent = heading.dataset.tocLabel || headingText(heading);
      item.append(link);
      list.append(item);
      return link;
    });
    host.append(list);

    // Scrollspy: mark the last heading whose top has passed the fold.
    const mark = (id) =>
      links.forEach((link) =>
        link.setAttribute("aria-current", String(link.hash === `#${id}`)),
      );

    if (!("IntersectionObserver" in window)) {
      mark(headings[0].id);
      return;
    }
    const seen = new Set();
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) seen.add(entry.target.id);
          else seen.delete(entry.target.id);
        });
        const current = headings.find((heading) => seen.has(heading.id));
        if (current) mark(current.id);
      },
      { rootMargin: "-10% 0px -70% 0px", threshold: 0 },
    );
    headings.forEach((heading) => observer.observe(heading));
    mark(headings[0].id);
  }

  /* ------------------------------------------------------------- samples */

  // A sounding broadcast: every data-* on the trigger fills the slot with the
  // matching data-sample-slot name, and swatches take it as a background.
  function initSample(trigger) {
    const group = trigger.closest("[data-sample-group]") || document;
    trigger.addEventListener("click", () => {
      all("[data-sample]", group).forEach((other) =>
        other.setAttribute("aria-pressed", String(other === trigger)),
      );
      Object.entries(trigger.dataset).forEach(([key, value]) => {
        all(`[data-sample-slot="${key}"]`, group).forEach((slot) => {
          if (slot.dataset.sampleSwatch !== undefined) slot.style.background = value;
          else slot.textContent = value;
        });
      });
    });
  }

  /* -------------------------------------------------------------- favicon */

  // A bundled document would otherwise carry the mark twice: once for the tab
  // icon and once for the masthead. Point the icon at the image already here.
  function initFavicon(image) {
    const link = document.querySelector('link[rel="icon"]') ||
      document.head.appendChild(Object.assign(document.createElement("link"), {
        rel: "icon",
      }));
    link.href = image.currentSrc || image.src;
  }

  /* ---------------------------------------------------------------- init */

  function init() {
    all("img[data-favicon]").forEach(initFavicon);
    all("[data-tabs]").forEach(initTabs);
    all("[data-sort-table]").forEach(initSortTable);
    all("[data-filter]").forEach(initFilter);
    all("[data-copy]").forEach(initCopy);
    all("[data-dialog]").forEach(initDialogTrigger);
    all("[data-anchors]").forEach(initAnchors);
    all("[data-toc]").forEach(initToc);
    all("[data-sample]").forEach(initSample);
    all("[data-toast]").forEach((button) =>
      button.addEventListener("click", () => toast(button.dataset.toast)),
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.harbor = { toast };
})();
