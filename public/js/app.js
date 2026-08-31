(function () {
  "use strict";

  var STATUS_LABELS = {
    "in-force": "In force",
    pipeline: "Pipeline",
    "enacted-not-commenced": "Enacted, not commenced",
    "not-scored": "Not scored"
  };

  var DOMAIN_LABELS = {
    criminal: "Criminal",
    "civil-protective-order": "Civil protective order",
    custody: "Custody",
    definitional: "Definitional"
  };

  var state = {
    rows: [],
    meta: {},
    geo: "all",
    status: "all",
    domain: "all",
    query: "",
    sortKey: "jurisdiction",
    sortDir: 1
  };

  function $(id) {
    return document.getElementById(id);
  }

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

  function searchBlob(row) {
    return [
      row.jurisdiction,
      row.jurisdictionCode,
      row.instrument,
      row.citation,
      row.status,
      row.domain,
      row.accomplishes,
      row.date,
      row.notes || ""
    ]
      .join(" ")
      .toLowerCase();
  }

  function geoMatch(row) {
    if (state.geo === "all") return true;
    if (state.geo === "us-state") {
      return row.geographyType === "us-state" || row.geographyType === "us-federal";
    }
    return row.geographyType === state.geo;
  }

  function statusMatch(row) {
    if (state.status === "all") return true;
    if (state.status === "pipeline") {
      return row.status === "pipeline" || row.status === "enacted-not-commenced";
    }
    return row.status === state.status;
  }

  function domainMatch(row) {
    if (state.domain === "all") return true;
    return row.domain === state.domain;
  }

  function visibleRows() {
    var q = state.query.trim().toLowerCase();
    return state.rows.filter(function (row) {
      if (!geoMatch(row)) return false;
      if (!statusMatch(row)) return false;
      if (!domainMatch(row)) return false;
      if (q && searchBlob(row).indexOf(q) === -1) return false;
      return true;
    }).slice().sort(function (a, b) {
      var ka = a[state.sortKey];
      var kb = b[state.sortKey];
      if (state.sortKey === "dateSort") {
        ka = a.dateSort || "";
        kb = b.dateSort || "";
      }
      ka = ka == null ? "" : String(ka);
      kb = kb == null ? "" : String(kb);
      return ka.localeCompare(kb) * state.sortDir;
    });
  }

  function headlineCounts(rows) {
    var us = {};
    var countries = {};
    var pipeline = 0;
    rows.forEach(function (row) {
      if (row.geographyType === "us-state" && row.status === "in-force" && row.namedTerm === true) {
        us[row.jurisdiction] = true;
      }
      if (
        row.geographyType === "country" &&
        row.status === "in-force" &&
        row.domain === "criminal" &&
        row.namedTerm === true
      ) {
        countries[row.jurisdiction] = true;
      }
      if ((row.status === "pipeline" || row.status === "enacted-not-commenced") && row.scored === true) {
        pipeline += 1;
      }
    });
    return {
      usStates: Object.keys(us).length,
      countries: Object.keys(countries).length,
      pipeline: pipeline
    };
  }

  function renderCounts() {
    var c = headlineCounts(state.rows);
    $("counts").innerHTML =
      card(c.usStates, "US states with a named-term law in force") +
      card(c.countries, "Countries and territories with a named-term criminal offence in force") +
      card(c.pipeline, "Pipeline instruments (named-term, not in force)");
  }

  function card(num, label) {
    return (
      '<div class="count-card"><span class="num">' +
      num +
      '</span><span class="lbl">' +
      escapeHtml(label) +
      "</span></div>"
    );
  }

  function renderTable() {
    var rows = visibleRows();
    $("results-meta").textContent = "Showing " + rows.length + " of " + state.rows.length + " instrument rows.";
    var body = $("tracker-body");
    if (!rows.length) {
      body.innerHTML = '<tr><td class="empty" colspan="8">No instruments match that search and filter.</td></tr>';
      postHeight();
      return;
    }
    body.innerHTML = rows
      .map(function (row) {
        var statusClass = row.status;
        var source = row.sourceUrl
          ? '<a href="' + escapeHtml(row.sourceUrl) + '" rel="noopener noreferrer">Official text</a>'
          : "";
        return (
          "<tr>" +
          "<td>" + escapeHtml(row.jurisdiction) + "</td>" +
          "<td>" + escapeHtml(row.instrument) + "</td>" +
          '<td><span class="badge ' + escapeHtml(statusClass) + '">' + escapeHtml(STATUS_LABELS[row.status] || row.status) + "</span></td>" +
          "<td>" + escapeHtml(DOMAIN_LABELS[row.domain] || row.domain) + "</td>" +
          "<td>" + escapeHtml(row.accomplishes) + "</td>" +
          "<td>" + escapeHtml(row.citation) + "</td>" +
          "<td>" + escapeHtml(row.date) + "</td>" +
          "<td>" + source + "</td>" +
          "</tr>"
        );
      })
      .join("");
    postHeight();
  }

  function renderMethod(payload) {
    var method = payload.method || [];
    $("method-copy").innerHTML = method
      .map(function (s) {
        return "<p>" + escapeHtml(s) + "</p>";
      })
      .join("");
    if (payload.lastUpdated) {
      $("updated-date").textContent = "Last updated " + payload.lastUpdated;
    }
  }

  function billLine(bill) {
    var title = (bill.title || "") + " " + ((bill.extras && bill.extras.title) || "");
    var blob = title.toLowerCase();
    var named = blob.indexOf("coercive control") !== -1;
    var substantive = /defin|offence|offense|felony|misdemeanor|crime|protective order|domestic/.test(blob);
    if (named && substantive) {
      return {
        mentionOnly: false,
        text: "This bill uses coercive control as a defined term or would create an offence or definition. Confirm against enrolled text before scoring as law."
      };
    }
    return {
      mentionOnly: true,
      text: "Mention only. This bill is not scored as a coercive control law."
    };
  }

  function latestAction(bill) {
    var acts = bill.latest_actions || bill.actions || [];
    if (acts.length) {
      var a = acts[0];
      var desc = a.description || a.action || "";
      var dt = a.date || "";
      return (dt ? dt + " " : "") + desc;
    }
    if (bill.latest_action) {
      var la = bill.latest_action;
      if (typeof la === "string") return la;
      return ((la.date || "") + " " + (la.description || "")).trim();
    }
    return bill.latest_action_description || "";
  }

  function renderBills(payload) {
    var body = $("bills-body");
    var results = (payload && payload.results) || [];
    if (!results.length) {
      body.innerHTML = '<tr><td class="empty" colspan="5">No live bill mentions returned.</td></tr>';
      postHeight();
      return;
    }
    body.innerHTML = results
      .map(function (bill) {
        var line = billLine(bill);
        var j = (bill.jurisdiction && (bill.jurisdiction.name || bill.jurisdiction)) || "";
        var id = bill.identifier || bill.id || "";
        var cls = line.mentionOnly ? "mention" : "";
        return (
          "<tr>" +
          "<td>" + escapeHtml(j) + "</td>" +
          "<td>" + escapeHtml(id) + "</td>" +
          "<td>" + escapeHtml(bill.title || "") + "</td>" +
          "<td>" + escapeHtml(latestAction(bill)) + "</td>" +
          '<td class="' + cls + '">' + escapeHtml(line.text) + "</td>" +
          "</tr>"
        );
      })
      .join("");
    postHeight();
  }

  function loadInstruments() {
    return fetch("data/instruments.json").then(function (res) {
      if (!res.ok) throw new Error("fetch");
      return res.json();
    });
  }

  function loadBills() {
    return fetch("/api/bills")
      .then(function (res) {
        if (!res.ok) throw new Error("fetch");
        return res.json();
      })
      .then(renderBills)
      .catch(function () {
        $("bills-body").innerHTML =
          '<tr><td class="empty" colspan="5">Open States results did not load. Seed data in the table above remains the named-term record.</td></tr>';
        postHeight();
      });
  }

  function bind() {
    $("search").addEventListener("input", function (e) {
      state.query = e.target.value;
      renderTable();
    });
    $("filter-geo").addEventListener("change", function (e) {
      state.geo = e.target.value;
      renderTable();
    });
    $("filter-status").addEventListener("change", function (e) {
      state.status = e.target.value;
      renderTable();
    });
    $("filter-domain").addEventListener("change", function (e) {
      state.domain = e.target.value;
      renderTable();
    });
    document.querySelectorAll("th[data-sort]").forEach(function (th) {
      th.addEventListener("click", function () {
        var key = th.getAttribute("data-sort");
        if (state.sortKey === key) state.sortDir *= -1;
        else {
          state.sortKey = key;
          state.sortDir = 1;
        }
        document.querySelectorAll("th[data-sort]").forEach(function (el) {
          el.removeAttribute("aria-sort");
        });
        th.setAttribute("aria-sort", state.sortDir === 1 ? "ascending" : "descending");
        renderTable();
      });
    });
  }

  loadInstruments()
    .then(function (payload) {
      state.rows = payload.instruments || [];
      renderMethod(payload);
      renderCounts();
      renderTable();
      bind();
      postHeight();
    })
    .catch(function () {
      $("tracker-body").innerHTML =
        '<tr><td class="empty" colspan="8">The tracker could not load instrument data. Open this folder through the local server at port 8765.</td></tr>';
      postHeight();
    });

  loadBills();

  window.addEventListener("load", postHeight);
  if (window.ResizeObserver) {
    var ro = new ResizeObserver(postHeight);
    ro.observe(document.documentElement);
  }
})();
