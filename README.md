# Coercive Control Named-Term Tracker

Carlton Research, LLC publishes this tracker. The count includes a statute only when the official text uses the words coercive control or coercive controlling, or the UK statutory phrase controlling or coercive behaviour. Nearby words such as coercion, controlling behavior, or emotional abuse do not qualify. Official statute text is the source.

A statute that names coercive control does not finish the work. The hard part is showing the pattern in a longitudinal record. Conflict, including hostility, is not that pattern.

Research, not legal advice. Carlton Research, LLC does not represent parties and does not make parenting-time recommendations.

## Run locally

```bash
python3 scripts/dev_server.py
```

Then open http://127.0.0.1:8765/

The local server serves `public/` and proxies `GET /api/bills` using the `OPENSTATES_API_KEY` value from `.env` on the server side. The browser never receives the key.

Validate the JSON lock:

```bash
python3 tests/validate.py
```


Appeals view: open http://127.0.0.1:8765/appeals.html . Expected live path: https://carlton-research-law-tracker.pages.dev/appeals.html . CourtListener REST search located candidate opinions. Holdings come from the opinions themselves (official court PDFs preferred). A published opinion that names coercive control does not finish the work. The hard part is showing the pattern in a longitudinal record.

Validate the appeals JSON:

```bash
python3 tests/validate_appeals.py
```


## Cloudflare Pages

Create a new Pages project named `carlton-research-law-tracker`. Set the output directory to `public`. Add `OPENSTATES_API_KEY` as a Pages environment variable. Do not name the project `hopeful-child-foundation`.

`wrangler.toml` already sets `pages_build_output_dir = "public"` and `compatibility_date = "2026-08-31"`.

## WordPress (page 2816)

Replace the content of WordPress page 2816 with a Custom HTML iframe pointing at the Pages URL. Do not add a second menu item. The live menu goes live only after Carisa confirms.

Placeholder iframe (swap the `src` after Pages is live):

```html
<iframe
  title="Coercive Control Named-Term Tracker"
  src="https://carlton-research-law-tracker.pages.dev/"
  style="width:100%;min-height:1400px;border:0;"
  loading="lazy"
></iframe>
```

## Method notes

Live Open States hits are mention search results. Mention-only bills are not scored as coercive control laws. Seed rows in `data/instruments.json` remain the named-term record.

Brand: Carlton Research, LLC. Public URL: https://carltonresearch.com/
