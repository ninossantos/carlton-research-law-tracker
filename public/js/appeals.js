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

  function docketBase(docket) {
    return String(docket || "")
      .toUpperCase()
      .replace(/\s+/g, "")
      .replace(/-(I|II|III|IV|V)$/i, "")
      .split("/")[0]
      .replace(/REL$/i, "")
      .replace(/(\d)[A-Z]$/i, "$1");
  }

  function titleKey(title) {
    return String(title || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .replace(/\b(v|vs|and)\b/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function caseKey(c) {
    var base = docketBase(c.docket);
    var abbr = c.stateAbbr || "";
    if (base.length >= 4) return abbr + "|d|" + base;
    return abbr + "|t|" + titleKey(c.title) + "|" + (c.dateSort || "");
  }

  function isPublished(c) {
    var s = String(c.status || "").toLowerCase();
    return s === "published" || s === "precedential";
  }

  function isStub(summary) {
    var s = String(summary || "").trim();
    if (!s) return true;
    if (s.indexOf("Published opinion that uses the words coercive control") === 0) return true;
    if (s.indexOf("The court names coercive control") === 0) return true;
    var low = s.toLowerCase();
    return low.indexOf("coercive control") === -1 && low.indexOf("controlling or coercive") === -1;
  }

  function rank(c) {
    var n = 0;
    if (isPublished(c)) n += 50;
    if (!isStub(c.summary)) n += 40;
    if (c.source === "official PDF") n += 15;
    n += Math.min(20, String(c.docket || "").length);
    n += Math.min(10, Math.floor(String(c.summary || "").length / 80));
    return n;
  }

  function mergeRow(a, b) {
    var win = rank(a) >= rank(b) ? a : b;
    var lose = win === a ? b : a;
    var out = {};
    Object.keys(lose).forEach(function (k) { out[k] = lose[k]; });
    Object.keys(win).forEach(function (k) { out[k] = win[k]; });
    if (isStub(win.summary) && !isStub(lose.summary)) out.summary = lose.summary;
    if (!isPublished(win) && isPublished(lose)) out.status = lose.status || out.status;
    if (win.source !== "official PDF" && lose.source === "official PDF") {
      out.opinionUrl = lose.opinionUrl || out.opinionUrl;
      out.source = "official PDF";
    }
    return out;
  }

  function dedupeCases(rows) {
    var best = {};
    var order = [];
    (rows || []).forEach(function (row) {
      var key = caseKey(row);
      if (!best[key]) {
        best[key] = row;
        order.push(key);
      } else {
        best[key] = mergeRow(best[key], row);
      }
    });
    return order.map(function (key) { return best[key]; });
  }

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
    state.cases = dedupeCases(payload.cases || []);
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
