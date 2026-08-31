/**
 * Cloudflare Pages Function. Proxies Open States v3.
 * Reads OPENSTATES_API_KEY from context.env only. Never echoes the key.
 */
export async function onRequest(context) {
  const key = context.env && context.env.OPENSTATES_API_KEY;
  if (!key) {
    return jsonResponse({ error: "Open States proxy is not configured." }, 500);
  }

  const incoming = new URL(context.request.url);
  const page = incoming.searchParams.get("page") || "1";
  const all = incoming.searchParams.get("all") === "1";

  const headers = { "X-API-KEY": key, Accept: "application/json" };

  async function fetchPage(pageNum) {
    const api = new URL("https://v3.openstates.org/bills");
    api.searchParams.set("q", '"coercive control"');
    api.searchParams.set("sort", "updated_desc");
    api.searchParams.set("per_page", "20");
    api.searchParams.set("page", String(pageNum));
    const res = await fetch(api.toString(), { headers });
    const text = await res.text();
    let body;
    try {
      body = JSON.parse(text);
    } catch (err) {
      return { ok: false, status: res.status, body: { error: "Open States returned a non-JSON body." } };
    }
    return { ok: res.ok, status: res.status, body };
  }

  try {
    if (!all) {
      const result = await fetchPage(page);
      return jsonResponse(result.body, result.ok ? 200 : result.status);
    }

    const first = await fetchPage(1);
    if (!first.ok) {
      return jsonResponse(first.body, first.status);
    }
    const results = Array.isArray(first.body.results) ? first.body.results.slice() : [];
    const lastPage = Math.min(Number(first.body.pagination && first.body.pagination.max_page) || 1, 13);
    for (let p = 2; p <= lastPage; p += 1) {
      const next = await fetchPage(p);
      if (!next.ok || !Array.isArray(next.body.results)) break;
      results.push.apply(results, next.body.results);
    }
    return jsonResponse({
      results: results,
      pagination: first.body.pagination || {},
      fetched_pages: lastPage
    }, 200);
  } catch (err) {
    return jsonResponse({ error: "Open States results did not load." }, 502);
  }
}

function jsonResponse(body, status) {
  return new Response(JSON.stringify(body), {
    status: status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "Content-Security-Policy": "frame-ancestors *"
    }
  });
}
