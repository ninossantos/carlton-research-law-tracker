(function () {
  "use strict";

  var US_STATES = [
    ["AL", "Alabama"], ["AK", "Alaska"], ["AZ", "Arizona"], ["AR", "Arkansas"],
    ["CA", "California"], ["CO", "Colorado"], ["CT", "Connecticut"], ["DE", "Delaware"],
    ["DC", "District of Columbia"], ["FL", "Florida"], ["GA", "Georgia"], ["HI", "Hawaii"],
    ["ID", "Idaho"], ["IL", "Illinois"], ["IN", "Indiana"], ["IA", "Iowa"],
    ["KS", "Kansas"], ["KY", "Kentucky"], ["LA", "Louisiana"], ["ME", "Maine"],
    ["MD", "Maryland"], ["MA", "Massachusetts"], ["MI", "Michigan"], ["MN", "Minnesota"],
    ["MS", "Mississippi"], ["MO", "Missouri"], ["MT", "Montana"], ["NE", "Nebraska"],
    ["NV", "Nevada"], ["NH", "New Hampshire"], ["NJ", "New Jersey"], ["NM", "New Mexico"],
    ["NY", "New York"], ["NC", "North Carolina"], ["ND", "North Dakota"], ["OH", "Ohio"],
    ["OK", "Oklahoma"], ["OR", "Oregon"], ["PA", "Pennsylvania"], ["RI", "Rhode Island"],
    ["SC", "South Carolina"], ["SD", "South Dakota"], ["TN", "Tennessee"], ["TX", "Texas"],
    ["UT", "Utah"], ["VT", "Vermont"], ["VA", "Virginia"], ["WA", "Washington"],
    ["WV", "West Virginia"], ["WI", "Wisconsin"], ["WY", "Wyoming"]
  ];

  var DISP_LABELS = {
    affirmed: "Affirmed",
    reversed: "Reversed",
    remanded: "Remanded",
    "affirmed-in-part": "Affirmed in part",
    "reversed-in-part": "Reversed in part"
  };

  var state = { cases: [], meta: {}, filter: "all" };

  function $(id) { return document.getElementById(id); }

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function postHeight() {
    var height = Math.max(
      document.body ? document.body.scrollHeight : 0,
      document.documentElement ? document.documentElement.scrollHeight : 0
    );
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: "cc-tracker-height", height: height }, "*");
    }
  }

  function fillSelect() {
    var sel = $("filter-state");
    US_STATES.forEach(function (pair) {
      var opt = document.createElement("option");
      opt.value = pair[0];
      opt.textContent = pair[1];
      sel.appendChild(opt);
    });
  }

  function selectedCases() {
    var rows = state.cases.slice();
    if (state.filter !== "all") {
      rows = rows.filter(function (c) { return c.stateAbbr === state.filter; });
    }
    rows.sort(function (a, b) {
      if (a.dateSort === b.dateSort) return (a.title || "").localeCompare(b.title || "");
      return a.dateSort < b.dateSort ? 1 : -1;
    });
    return rows;
  }

  function renderUpdated(payload) {
    var stamp = (payload && payload.lastUpdated) || (payload && payload.meta && payload.meta.lastUpdated);
    if (stamp) {
      $("updated-date").textContent = "Last updated " + stamp;
    }
  }

  function renderCounts() {
    var byState = {};
    state.cases.forEach(function (c) {
      if (c.stateAbbr && c.stateAbbr !== "US") byState[c.stateAbbr] = true;
    });
    var nStates = Object.keys(byState).length;
    $("counts").innerHTML =
      '<div class="count-card"><span class="num">' + state.cases.length +
      '</span><span class="lbl">Appellate opinions</span></div>' +
      '<div class="count-card"><span class="num">' + nStates +
      '</span><span class="lbl">Jurisdictions with at least one opinion</span></div>' +
      '<div class="count-card"><span class="num">' + Math.max(0, 51 - nStates) +
      '</span><span class="lbl">States or D.C. with none in this tracker yet</span></div>';
  }

  function cardHtml(c) {
    var disp = DISP_LABELS[c.disposition] || c.disposition || "";
    var badges = "";
    if (disp) badges += '<span class="badge">' + escapeHtml(disp) + "</span> ";
    if (c.remanded) badges += '<span class="badge">Remanded</span> ';
    if (c.status) badges += '<span class="badge">' + escapeHtml(c.status) + "</span>";
    var cite = c.citation ? " · " + escapeHtml(c.citation) : "";
    return (
      '<article class="appeal-card">' +
      "<h2>" + escapeHtml(c.title) + "</h2>" +
      '<p class="appeal-meta">' + escapeHtml(c.docket) + " · " +
      escapeHtml(c.court) + " · " + escapeHtml(c.date) + cite + "</p>" +
      (badges ? "<p>" + badges + "</p>" : "") +
      "<p>" + escapeHtml(c.summary) + "</p>" +
      '<p class="appeal-links"><a href="' + escapeHtml(c.opinionUrl) +
      '" rel="noopener">Read the full opinion</a></p>' +
      "</article>"
    );
  }

  function renderCards() {
    var grid = $("appeal-grid");
    var rows = selectedCases();
    var meta = $("results-meta");
    if (!rows.length) {
      var label = "All states and D.C.";
      if (state.filter !== "all") {
        US_STATES.forEach(function (pair) {
          if (pair[0] === state.filter) label = pair[1];
        });
      }
      grid.innerHTML =
        '<p class="empty-state">No published appellate opinion naming coercive control is in this tracker yet.</p>';
      meta.textContent = label + ": 0 opinions in this tracker yet.";
      postHeight();
      return;
    }
    grid.innerHTML = rows.map(cardHtml).join("");
    meta.textContent = rows.length === 1
      ? "1 appellate opinion in this selection."
      : rows.length + " appellate opinions in this selection.";
    postHeight();
  }

  function applyPayload(payload) {
    state.cases = payload.cases || [];
    state.meta = payload.meta || {};
    renderUpdated(payload.meta || payload);
    renderCounts();
    renderCards();
    postHeight();
  }

  function loadAppeals() {
    return fetch("/api/appeals")
      .then(function (res) {
        if (!res.ok) throw new Error("live");
        return res.json();
      })
      .then(function (payload) {
        if (!payload || !Array.isArray(payload.cases) || !payload.cases.length) {
          throw new Error("empty");
        }
        applyPayload(payload);
      })
      .catch(function () {
        return fetch("/data/appeals.json")
          .then(function (res) {
            if (!res.ok) throw new Error("fetch");
            return res.json();
          })
          .then(applyPayload);
      });
  }

  fillSelect();
  $("filter-state").addEventListener("change", function (e) {
    state.filter = e.target.value;
    renderCards();
  });

  loadAppeals().catch(function () {
    $("appeal-grid").innerHTML =
      '<p class="empty-state">The tracker could not load appeals data.</p>';
    postHeight();
  });

  window.addEventListener("load", postHeight);
  if (window.ResizeObserver) {
    var ro = new ResizeObserver(postHeight);
    ro.observe(document.documentElement);
  }
})();
