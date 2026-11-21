/* ExamPulse 1000 - Post-exam analytics interactions */
(function () {
  "use strict";

  const shell = document.getElementById("reportShell");

  if (shell) {
    const tabs = Array.prototype.slice.call(document.querySelectorAll(".filter-tab"));
    const cards = Array.prototype.slice.call(document.querySelectorAll(".review-card"));
    const empty = document.getElementById("emptyFilter");

    function applyFilter(filter) {
      let visible = 0;
      cards.forEach(function (card) {
        const match = filter === "all" || card.dataset.status === filter;
        card.hidden = !match;
        if (match) visible += 1;
      });
      tabs.forEach(function (tab) {
        tab.classList.toggle("active", tab.dataset.filter === filter);
        tab.setAttribute("aria-selected", tab.dataset.filter === filter ? "true" : "false");
      });
      if (empty) empty.hidden = visible !== 0;
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () { applyFilter(tab.dataset.filter); });
    });

    // Animate report bars after paint.
    requestAnimationFrame(function () {
      document.querySelectorAll(".topic-track i, .metric-bar").forEach(function (bar) {
        const target = bar.style.getPropertyValue("--w");
        bar.style.width = "0%";
        requestAnimationFrame(function () { bar.style.width = target || "0%"; });
      });
    });

    if (window.REPORT_BOOT) {
      const report = window.REPORT_BOOT;
      document.title = "Report " + report.code + " · " + report.percentage + "% · ExamPulse 1000";
    }
  }
})();
