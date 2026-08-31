# carltonresearch.com hosting and page 2816 iframe plan

Verified 31 August 2026 (PT). No WordPress login. No live-page edits. No Hopeful Child product work.

Live page to replace later (same URL, same ID):  
https://carltonresearch.com/coercive-control-statute-map/  
WordPress page **id 2816**.

---

## 1. What is live now

Public REST (no auth):

https://carltonresearch.com/wp-json/wp/v2/pages/2816?_fields=id,slug,link,title,status,template,date,modified

| Field | Value |
|---|---|
| id | 2816 |
| slug | coercive-control-statute-map |
| status | publish |
| link | https://carltonresearch.com/coercive-control-statute-map/ |
| title | US Coercive Control Statutes: Named-Term Tracker |
| template | `""` (theme default, not a custom template slug) |
| date (UTC) | 2026-08-29T16:08:32 → **9:08 AM PT, 29 Aug 2026** |
| modified (UTC) | 2026-08-29T16:11:33 → **9:11 AM PT, 29 Aug 2026** |

Site identity from `https://carltonresearch.com/wp-json/` (no keys printed):

- name: Carlton Research, LLC
- description: Forensic analysis of coercive control for family-law matters.
- url / home: https://carltonresearch.com
- show_on_front: page; page_on_front 584; page_for_posts 587

Do **not** create a second page. The iframe swap is an edit of 2816 so the permalink stays `/coercive-control-statute-map/`.

---

## 2. DNS

Google DNS (`dns.google`) on 31 Aug 2026:

| Record | Name | Data |
|---|---|---|
| A | carltonresearch.com | **45.77.205.136** (TTL 300) |
| AAAA | carltonresearch.com | none |
| NS | carltonresearch.com | **evangeline.ns.cloudflare.com.**, **martin.ns.cloudflare.com.** |
| MX | carltonresearch.com | Zoho (10 mx.zoho.com, 20 mx2, 50 mx3) |
| TXT | carltonresearch.com | Zoho verification + `v=spf1 include:zohomail.com ~all` |
| A | www.carltonresearch.com | **104.21.7.142**, **172.67.187.151** (Cloudflare anycast) |
| AAAA | www.carltonresearch.com | 2606:4700:3036::6815:78e, 2606:4700:3037::ac43:bb97 |
| CNAME | www | none advertised (orange-cloud A/AAAA) |

Read of that split:

- Nameservers are **Cloudflare**.
- **www** is Cloudflare-proxied (orange cloud).
- **Apex** A is a single origin IP, **not** a Cloudflare proxy address. Apex is DNS-only (grey cloud) to the origin.

ipinfo.io on 45.77.205.136:

- Hostname: `45.77.205.136.vultrusercontent.com`
- ASN AS20473 The Constant Company, LLC (Vultr)
- Company: Vultr Holdings, LLC
- Location: Piscataway, NJ
- Hosting, not residential

That origin pattern (Vultr VM + Cloudflare DNS, apex grey / www orange) is the Cloudways-on-Vultr layout used on this account’s WordPress apps. It is **not** Bluehost (no Bluehost NS, no Bluehost A-block). It is **not** a Cloudflare origin for the apex.

---

## 3. HTTP headers

Direct `curl -sI` and Python `HEAD` to the live page were **blocked by Auto-review** in this environment. Headers were therefore not captured here.

A prior agent saved `/workspace/statute-map-audit/live.html` from a fetch of this URL. That file is an **Imunify360 / bot-challenge interstitial** (“Please wait while your request is being verified…”, form POST to `/z0f76a1d14fd21a8fb5fd0d03e0fdc3d3cedae52f`). Imunify360 on a Vultr origin is the default Cloudways WAF, not Bluehost and not Cloudflare’s challenge page.

WebFetch of the same URL from the fetch provider **did** return the published page (named-term tracker copy, last updated August 28, 2026). So the origin is WordPress; some automated clients hit the WAF first.

---

## 4. HTML generator / theme / plugins (no login)

### Kadence theme

`https://carltonresearch.com/wp-content/themes/kadence/style.css` is public. Header:

```
Theme Name: Kadence
Theme URI: https://www.liquidweb.com/software/kadence/
Author: Kadence WP
Version: 1.5.2
Text Domain: kadence
Requires at least: 6.3
Tested up to: 6.9.1
```

Kadence 1.5.2 is the active theme.

### REST namespaces (stack, not a login)

From `/wp-json/` (public index). Namespaces that identify vendors:

| Namespace | Means |
|---|---|
| `wp/v2` | WordPress |
| `kadence-starter-library/v1`, `kbp/v1`, `kbpp/v1`, `kb-*` | Kadence theme + Kadence Blocks (+ Pro) |
| `liquidweb/harbor/v1` | Liquid Web Harbor (Kadence/Liquid Web licensing/updates) |
| `jetpack/v4`, `jetpack-boost/v1`, `wpcom/v2` | Jetpack / WordPress.com connection |
| `wordfence/v1`, `wordfence-login-security/v1` | Wordfence |
| `yoast/v1` | Yoast SEO |
| `redirection/v1` | Redirection plugin |
| `code-snippets/v1` | Code Snippets |
| `slimstat/v1` | Slimstat analytics |

Not present: Bluehost, SiteGround, WP Engine, Kinsta, Elementor, Divi.

### Hosting conclusion

| Layer | What |
|---|---|
| Registrar/DNS | Cloudflare nameservers |
| CDN / proxy | Cloudflare on **www** only; apex is origin |
| Origin compute | Vultr VM `45.77.205.136` |
| Origin platform | **Cloudways-class managed WordPress** (Vultr + Imunify360 challenge). Not Bluehost. |
| CMS | WordPress |
| Theme | **Kadence 1.5.2** |
| Builder | Kadence Blocks (and Pro, from `kbpp`) |
| WAF / login security | Wordfence + origin Imunify360 |
| Mail | Zoho |

Memory logs of other agents (not Hopeful Child product copy): Cloudways is the user’s WordPress host of record; a Cloudways server at this same origin IP previously ran multiple apps. That is consistent with the DNS/origin facts above. This file does not reuse Hopeful Child product details.

---

## 5. Iframe plan to **replace** page 2816 (not a second page)

Goal: keep `https://carltonresearch.com/coercive-control-statute-map/` and WP id **2816**. Swap the body for a full-width iframe of the tracker app. Do this later, in wp-admin, as the user. Do not do it from this box.

### 5.1 Edit 2816, do not duplicate

1. Pages → search slug `coercive-control-statute-map` (id 2816).
2. Do not Add New. Do not change the slug.
3. Replace the existing blocks with the iframe block below.
4. Update. Permalink stays the same.

### 5.2 Kadence page settings (2816)

Because `template` is empty, use the Kadence page sidebar / document settings:

- Layout: **Full Width** (or Unboxed), **disable sidebar**, disable title if the tracker has its own H1.
- Content max-width: none / full, so the iframe is not trapped at ~800px.
- Featured image: none needed.

### 5.3 Block to paste (Kadence Custom HTML or core Custom HTML)

Use a real tracker origin when it exists (Cloudflare Pages, GitHub Pages, etc.). Placeholder below; do not point at a second WP page.

```html
<div class="cc-statute-map-embed">
  <iframe
    id="cc-statute-map"
    title="US coercive control named-term statute map"
    src="https://TRACKER-ORIGIN.example/index.html"
    loading="eager"
    referrerpolicy="no-referrer-when-downgrade"
    allow="clipboard-write"
    style="width:100%;height:calc(100vh - 120px);min-height:720px;border:0;display:block;background:#fff;">
  </iframe>
</div>
```

Optional Code Snippet (site-wide CSS, or a Kadence Custom CSS box on 2816 only):

```css
.cc-statute-map-embed { margin: 0; padding: 0; }
body.page-id-2816 .entry-content,
body.page-id-2816 .kb-section-container {
  max-width: none !important;
  padding-left: 0;
  padding-right: 0;
}
```

If the tracker URL is not yet public, leave `src` as a staging URL the user controls. Do not iframe carltonresearch.com inside itself.

### 5.4 Headers / WAF notes for the **tracker** origin (not WP)

- Tracker must send `Content-Security-Policy` that does not forbid being framed, **or** send `Content-Security-Policy: frame-ancestors https://carltonresearch.com https://www.carltonresearch.com`.
- Do **not** send `X-Frame-Options: DENY` or `SAMEORIGIN` on the tracker. SAMEORIGIN would block the WP embed.
- WordPress/Kadence does not need to allow being framed; it is the parent.

### 5.5 Wordfence / Imunify360 / Cloudflare

- Origin Imunify360 already challenges some bots on the WP URL. After the swap, humans still load 2816 first; the iframe is a second origin. If the tracker is on Cloudflare Pages, it will not share the Imunify360 challenge.
- Wordfence on WP does not filter the iframe **contents**. It can still challenge the parent page for suspicious clients.
- www is Cloudflare-proxied; apex is not. Use one canonical (www or apex) in the iframe `src` allowlist and in `frame-ancestors`. Today the public page is the **apex** URL.

### 5.6 What not to do

- Do not add a new page (new id, new slug, `/statute-map-app/` etc.).
- Do not log in from this environment to push the edit.
- Do not put API keys, Wordfence keys, Jetpack keys, or Kadence license keys in the iframe markup or in this repo. None are printed here.
- Do not clone repos for this task.

### 5.7 Later verification checklist (after a human publishes the edit)

- `https://carltonresearch.com/coercive-control-statute-map/` still 200, still id 2816.
- One iframe, tracker visible, Kadence header/footer still wrap it unless the user asks to hide them.
- View-source still shows Kadence / wp-content; the map itself is the framed app.
- REST `pages/2816` title can stay; body HTML will contain the iframe.

---

## 6. Sources used

- DNS: Google DNS-over-HTTPS
- Origin IP: ipinfo.io/45.77.205.136
- Theme: public `/wp-content/themes/kadence/style.css`
- REST: public `/wp-json/` and `/wp-json/wp/v2/pages/2816`
- Live copy: WebFetch of the public URL (tracker prose, not generator meta)
- WAF interstitial: `/workspace/statute-map-audit/live.html` (prior agent capture)
- HTTP response headers: **not captured** (shell HEAD blocked)

