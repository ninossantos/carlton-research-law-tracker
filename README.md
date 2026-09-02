# Coercive Control Law Tracker

Carlton Research, LLC publishes this tracker. The count includes a statute only when the official text uses the words coercive control or coercive controlling, or the UK statutory phrase controlling or coercive behaviour. Nearby words such as coercion, controlling behavior, or emotional abuse do not qualify. Official statute text is the source.

A statute that names coercive control does not finish the work. The hard part is showing the pattern in a longitudinal record. Conflict, including hostility, is not that pattern.

Research, not legal advice. Carlton Research, LLC does not represent parties and does not make parenting-time recommendations.

Live URLs:

- Statutes: https://tracker.carltonresearch.com/
- Appeals: https://tracker.carltonresearch.com/appeals

Do not invent a second tracker URL.

## Auto update

- **Statutes / bills:** `/api/bills` reads Open States on the page load. New legislative mentions appear without a manual edit. Mention-only bills are not scored as coercive control laws. Scored in-force rows still come from official statute text in `data/instruments.json`.
- **Appeals:** `/api/appeals` reads CourtListener on the page load and caches the result for six hours. A Monday GitHub Action also writes `data/appeals.json` so the static file stays current if CourtListener is down. No manual list management.

Optional Cloudflare and GitHub secret: `COURTLISTENER_TOKEN`. Open States already uses `OPENSTATES_API_KEY`.

## Run locally

```bash
python3 scripts/dev_server.py
```

Then open http://127.0.0.1:8765/

The local server serves `public/` and proxies `GET /api/bills` using the `OPENSTATES_API_KEY` value from `.env` on the server side. The browser never receives the key. Local `/api/appeals` serves the saved JSON.

Validate the JSON lock:

```bash
python3 tests/validate.py
```

Refresh the appeals backup from CourtListener:

```bash
python3 scripts/refresh_appeals.py
```

Validate the appeals JSON:

```bash
python3 tests/validate_appeals.py
```

## Cloudflare Pages

Pages project: `carlton-research-law-tracker`. Output directory: `public`. Environment variables: `OPENSTATES_API_KEY`, optional `COURTLISTENER_TOKEN`.

## Brand

Carlton Research, LLC. Public URL: https://carltonresearch.com/
