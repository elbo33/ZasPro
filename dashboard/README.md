# ZasPro dashboard

Read-mostly Next.js (App Router) dashboard for M3+ (SPEC §16). It calls the
FastAPI backend and never touches Postgres directly.

## Pages

| route            | what                                                            |
|------------------|----------------------------------------------------------------|
| `/`              | review queue — one item per screen, keyboard only, no reloads |
| `/curriculum`    | podstawowy requirement tree with mapped / approved / exercise counts |
| `/sources`       | ingested documents; click through to per-chunk mapping status |
| `/sources/[id]`  | a document's chunks, each with its mapping status             |

## Review keyboard map

Displayed along the bottom of the page. No mouse needed.

| key        | action                                              |
|------------|-----------------------------------------------------|
| `a`        | approve the current mapping                          |
| `r`        | enter reject mode, then `1`–`6` picks a reason code (Esc cancels) |
| `e`        | enter edit mode, `j`/`k` move the topic selection, `Enter` applies, Esc cancels |
| `s`        | skip (excluded from `next` this session, not resolved) |
| `b`        | batch-approve every open item in the current item's `(topic, source)` group |

Reason codes: `1` WRONG_TOPIC · `2` WRONG_CONTENT_TYPE · `3` NOT_CURRICULUM ·
`4` AMBIGUOUS · `5` LOW_QUALITY_SOURCE · `6` OTHER.

## Running it

```bash
# 1. backend (repo root)
uv run uvicorn zaspro.api.app:app --port 8000

# 2. produce a queue to review (offline stub agent if no ANTHROPIC_API_KEY)
uv run python -m zaspro.mapping.run MMAP-P0-660-A-2405-arkusz.docx

# 3. dashboard (this directory)
npm install
npm run dev            # http://localhost:3000
```

The API base defaults to `http://localhost:8000`; override with
`NEXT_PUBLIC_API_BASE`. The reviewer name is read from `localStorage`
(`zaspro.reviewer`, default `"reviewer"`).
