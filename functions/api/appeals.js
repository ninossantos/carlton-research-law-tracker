/**
 * Cloudflare Pages Function. Harvests CourtListener opinions that use
 * the words coercive control. Same host: /api/appeals.
 * Optional COURTLISTENER_TOKEN from context.env. Never echoes the token.
 */

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const FEDERAL_IDS = {
  scotus: 1, ca1: 1, ca2: 1, ca3: 1, ca4: 1, ca5: 1, ca6: 1, ca7: 1,
  ca8: 1, ca9: 1, ca10: 1, ca11: 1, cadc: 1, cafc: 1, ccpa: 1,
};

const COURT_STATE = {
  ala: "AL", alactapp: "AL", alacrimapp: "AL", alcivapp: "AL",
  alaska: "AK", alaskactapp: "AK",
  ariz: "AZ", arizctapp: "AZ", ariztaxct: "AZ",
  ark: "AR", arkctapp: "AR",
  cal: "CA", calctapp: "CA", calappdeptsuper: "CA",
  colo: "CO", coloctapp: "CO",
  conn: "CT", connappct: "CT", connsuperct: "CT",
  del: "DE", delch: "DE", delsuperct: "DE",
  dc: "DC", dcappeals: "DC",
  fla: "FL", fladistctapp: "FL",
  ga: "GA", gactapp: "GA",
  haw: "HI", hawapp: "HI",
  idaho: "ID",
  ill: "IL", illappct: "IL",
  ind: "IN", indctapp: "IN",
  iowa: "IA", iowactapp: "IA",
  kan: "KS", kanctapp: "KS",
  ky: "KY", kyctapp: "KY",
  la: "LA", lactapp: "LA",
  me: "ME",
  md: "MD", mdctspecapp: "MD", mdctapp: "MD",
  mass: "MA", massappct: "MA",
  mich: "MI", michctapp: "MI",
  minn: "MN", minnctapp: "MN",
  miss: "MS", missctapp: "MS",
  mo: "MO", moctapp: "MO",
  mont: "MT",
  neb: "NE", nebctapp: "NE",
  nev: "NV",
  nh: "NH",
  nj: "NJ", njsuperctappdiv: "NJ", njtaxct: "NJ",
  nm: "NM", nmctapp: "NM",
  ny: "NY", nyappdiv: "NY", nyappterm: "NY", nyfamct: "NY",
  nc: "NC", ncctapp: "NC",
  nd: "ND",
  ohio: "OH", ohioctapp: "OH",
  okla: "OK", oklacivapp: "OK", oklacrimapp: "OK",
  or: "OR", orctapp: "OR",
  pa: "PA", pasuperct: "PA", pacommwct: "PA",
  ri: "RI",
  sc: "SC", scctapp: "SC",
  sd: "SD",
  tenn: "TN", tennctapp: "TN", tenncrimapp: "TN",
  tex: "TX", texapp: "TX", texcrimapp: "TX",
  utah: "UT", utahctapp: "UT",
  vt: "VT",
  va: "VA", vactapp: "VA",
  wash: "WA", washctapp: "WA", washterr: "WA",
  wva: "WV",
  wis: "WI", wisctapp: "WI",
  wyo: "WY",
};

const STATE_NAMES = {
  AL: "Alabama", AK: "Alaska", AZ: "Arizona", AR: "Arkansas", CA: "California",
  CO: "Colorado", CT: "Connecticut", DE: "Delaware", DC: "District of Columbia",
  FL: "Florida", GA: "Georgia", HI: "Hawaii", ID: "Idaho", IL: "Illinois",
  IN: "Indiana", IA: "Iowa", KS: "Kansas", KY: "Kentucky", LA: "Louisiana",
  ME: "Maine", MD: "Maryland", MA: "Massachusetts", MI: "Michigan", MN: "Minnesota",
  MS: "Mississippi", MO: "Missouri", MT: "Montana", NE: "Nebraska", NV: "Nevada",
  NH: "New Hampshire", NJ: "New Jersey", NM: "New Mexico", NY: "New York",
  NC: "North Carolina", ND: "North Dakota", OH: "Ohio", OK: "Oklahoma",
  OR: "Oregon", PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina",
  SD: "South Dakota", TN: "Tennessee", TX: "Texas", UT: "Utah", VT: "Vermont",
  VA: "Virginia", WA: "Washington", WV: "West Virginia", WI: "Wisconsin", WY: "Wyoming",
};

const NAME_TO_ABBR = Object.fromEntries(
  Object.entries(STATE_NAMES).map(([abbr, name]) => [name.toLowerCase(), abbr]),
);

function formatDate(iso) {
  if (!iso || iso.length < 10) return iso || "";
  const y = iso.slice(0, 4);
  const m = Number(iso.slice(5, 7));
  const d = Number(iso.slice(8, 10));
  if (!m || !MONTHS[m - 1]) return iso;
  return MONTHS[m - 1] + " " + d + ", " + y;
}

function todayStamp() {
  const now = new Date();
  return MONTHS[now.getUTCMonth()] + " " + now.getUTCDate() + ", " + now.getUTCFullYear();
}

function slug(s) {
  return String(s || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

function placeFor(hit) {
  const id = hit.court_id || "";
  if (FEDERAL_IDS[id] || id.indexOf("ca") === 0 && /^ca\d+$/.test(id)) {
    return { state: "Federal", stateAbbr: "US" };
  }
  if (COURT_STATE[id]) {
    const abbr = COURT_STATE[id];
    return { state: STATE_NAMES[abbr], stateAbbr: abbr };
  }
  const court = String(hit.court || "");
  for (const [name, abbr] of Object.entries(NAME_TO_ABBR)) {
    if (court.toLowerCase().indexOf(name) !== -1) {
      return { state: STATE_NAMES[abbr], stateAbbr: abbr };
    }
  }
  return null;
}

function isUs(hit) {
  return placeFor(hit) !== null;
}

function mapHit(hit, seedByDocket, seedByTitle) {
  const place = placeFor(hit);
  if (!place) return null;
  const docket = hit.docketNumber || "";
  const title = hit.caseName || "Untitled opinion";
  const seed =
    (docket && seedByDocket[docket.replace(/\s+/g, "")]) ||
    seedByTitle[title.toLowerCase()] ||
    null;
  const iso = hit.dateFiled || "";
  const cites = Array.isArray(hit.citation) ? hit.citation.join("; ") : hit.citation || hit.neutralCite || "";
  const urlPath = hit.absolute_url || "";
  const liveUrl = urlPath
    ? (urlPath.indexOf("http") === 0 ? urlPath : "https://www.courtlistener.com" + urlPath)
    : "";
  const syllabus = (hit.syllabus || "").replace(/\s+/g, " ").trim();
  const summary = seed
    ? seed.summary
    : syllabus
      ? syllabus.slice(0, 900)
      : "Published opinion that uses the words coercive control. Read the full opinion.";
  return {
    id: seed ? seed.id : slug((hit.court_id || "op") + "-" + docket + "-" + iso),
    state: place.state,
    stateAbbr: place.stateAbbr,
    court: hit.court || (seed && seed.court) || "",
    title: title,
    docket: docket,
    citation: seed && seed.citation ? seed.citation : cites,
    date: formatDate(iso),
    dateSort: iso,
    disposition: seed ? seed.disposition : "",
    remanded: seed ? Boolean(seed.remanded) : false,
    summary: summary,
    opinionUrl: seed && seed.opinionUrl && seed.source === "official PDF" ? seed.opinionUrl : liveUrl,
    source: seed && seed.source === "official PDF" ? "official PDF" : "CourtListener",
    status: hit.status || "",
  };
}

async function fetchJson(url, token) {
  const headers = {
    Accept: "application/json",
    "User-Agent": "CarltonResearchTracker/1.0 (https://tracker.carltonresearch.com/; appeals harvest)",
  };
  if (token) headers.Authorization = "Token " + token;
  const res = await fetch(url, { headers });
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch (err) {
    return { ok: false, status: res.status, body: null };
  }
  return { ok: res.ok, status: res.status, body: body };
}

function jsonResponse(body, status, extraHeaders) {
  const headers = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "public, s-maxage=21600, max-age=300",
    "Content-Security-Policy": "frame-ancestors *",
  };
  if (extraHeaders) Object.assign(headers, extraHeaders);
  return new Response(JSON.stringify(body), { status: status, headers: headers });
}

export async function onRequest(context) {
  const token = (context.env && context.env.COURTLISTENER_TOKEN) || "";
  const cache = caches.default;
  const cacheKey = new Request("https://tracker.carltonresearch.com/__cache/appeals-v1");
  const hit = await cache.match(cacheKey);
  if (hit) return hit;

  const origin = new URL(context.request.url).origin;
  let seedCases = [];
  try {
    const seedRes = await fetch(origin + "/data/appeals.json");
    if (seedRes.ok) {
      const seedJson = await seedRes.json();
      seedCases = Array.isArray(seedJson.cases) ? seedJson.cases : [];
    }
  } catch (err) {
    seedCases = [];
  }
  const seedByDocket = {};
  const seedByTitle = {};
  seedCases.forEach(function (row) {
    if (row.docket) seedByDocket[String(row.docket).replace(/\s+/g, "")] = row;
    if (row.title) seedByTitle[String(row.title).toLowerCase()] = row;
  });

  const collected = [];
  let url =
    "https://www.courtlistener.com/api/rest/v4/search/?q=%22coercive%20control%22&type=o&order_by=dateFiled%20desc";
  let pages = 0;
  let liveFailed = false;
  while (url && pages < 10) {
    const result = await fetchJson(url, token);
    pages += 1;
    if (!result.ok || !result.body || !Array.isArray(result.body.results)) {
      liveFailed = pages === 1;
      break;
    }
    result.body.results.forEach(function (row) {
      if (!isUs(row)) return;
      const mapped = mapHit(row, seedByDocket, seedByTitle);
      if (mapped) collected.push(mapped);
    });
    url = result.body.next || "";
  }

  if (liveFailed && seedCases.length) {
    const fallback = jsonResponse(
      {
        meta: {
          title: "Coercive Control Appeal Tracker",
          lastUpdated: todayStamp(),
          sourceNote:
            "Live CourtListener harvest did not complete. Showing the last saved set. Research, not legal advice.",
          live: false,
          count: seedCases.length,
        },
        cases: seedCases,
      },
      200,
    );
    return fallback;
  }

  const seen = {};
  const cases = [];
  collected.forEach(function (row) {
    const key = (row.docket || row.title) + "|" + row.dateSort;
    if (seen[key]) return;
    seen[key] = true;
    cases.push(row);
  });
  seedCases.forEach(function (row) {
    const key = (row.docket || row.title) + "|" + (row.dateSort || "");
    if (seen[key]) return;
    seen[key] = true;
    cases.push(row);
  });

  const payload = {
    meta: {
      title: "Coercive Control Appeal Tracker",
      lastUpdated: todayStamp(),
      sourceNote:
        "CourtListener search of United States opinions that use the words coercive control. The list updates automatically. Research, not legal advice.",
      live: true,
      count: cases.length,
    },
    cases: cases,
  };
  const response = jsonResponse(payload, 200);
  try {
    await cache.put(cacheKey, response.clone());
  } catch (err) {
    // Cache write is best-effort.
  }
  return response;
}
