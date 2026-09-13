// Pure on-page filter over already-loaded <details class="rule"> blocks.
// No fetch, no dependencies, no external index — works fully offline and
// is unaffected by back/forward navigation since it never touches history.
(function () {
  var box = document.getElementById("rule-search");
  if (!box) return;
  var rules = Array.prototype.slice.call(document.querySelectorAll("details.rule"));
  var groups = Array.prototype.slice.call(document.querySelectorAll("[data-group]"));
  var countEl = document.getElementById("search-count");

  function apply() {
    var q = box.value.trim().toLowerCase();
    var shown = 0;
    rules.forEach(function (el) {
      var hay = el.getAttribute("data-search") || "";
      var match = q === "" || hay.indexOf(q) !== -1;
      el.hidden = !match;
      if (match) shown++;
      if (q !== "" && match) el.open = true;
      if (q === "") el.open = el.hasAttribute("data-was-open");
    });
    groups.forEach(function (g) {
      var anyVisible = g.querySelectorAll("details.rule:not([hidden])").length > 0;
      g.hidden = !anyVisible;
    });
    if (countEl) {
      countEl.textContent = q === "" ? "" : shown + " of " + rules.length + " rules match";
    }
  }

  box.addEventListener("input", apply);

  var collapseBtn = document.getElementById("collapse-toggle");
  if (collapseBtn) {
    collapseBtn.addEventListener("click", function () {
      var collapsing = collapseBtn.textContent.trim() === "Collapse all";
      rules.forEach(function (el) { el.open = !collapsing; });
      collapseBtn.textContent = collapsing ? "Expand all" : "Collapse all";
    });
  }
})();
