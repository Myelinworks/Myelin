# Handoff — backend

Written 22 Aug 2026. Everything below is either in `main` or is a decision someone has to
make; nothing here is speculation about work that was not done.

## What changed in this session

| Commit | What it is |
| --- | --- |
| `1f4a97a` | `budget()` reports `investment` (the signed Path A cheque) alongside `drawn`, so a client can name the thing that raised the Q4 ceiling instead of re-deriving it. |
| `d5f18c4` | **Bug fix.** Scoring read the crisis commitment from `result.lines["_crisis_commit"]` — a key nothing has ever written. `commit` was therefore always zero: every crisis quarter collected the −4 "market event ignored" modifier and Adaptability graded the response as "none", however many lakhs went behind it. The result now carries `crisis_commit` beside `crisis_variant`/`crisis_strategy`. |
| `1773156` | `tests/e2e/` — three personas play a whole run over HTTP. See below. |

## The e2e suite

`tests/e2e/` drives the API end to end: create the company, preview and lock four quarters,
sign a term sheet between Q3 and Q4, settle it. Three personas (`personas.py`) decide only
from what the responses tell them — none of them reads engine internals — and all three face
the same market event, so the only variable is how they played.

```
uv run pytest tests/e2e -s      # with the comparison table
uv run pytest -m "not e2e"      # everything else; these are the slow, DB-backed ones
```

It is not a smoke test. A single scripted run only proves the machinery does not fall over;
three runs played well and badly assert that the machinery *discriminates*. Current spread:

```
CEO                             Q1    Q2    Q3    Q4   mean  band        path   tier
Novice · buys leads           26.3   5.8   1.8  -2.2    7.9  Poor           C   DISTRESSED
Intermediate · spreads evenly 46.1  42.0  32.0  65.0   46.3  Competent      A   DISTRESSED
Expert · funds the constraint 43.7  49.2  58.8  64.1   54.0  Competent      A   STABLE
```

If a persona rewrite ever makes the novice score like the expert, that is a finding about the
rubric, not a test to relax.

## Open questions the code will not answer

1. **A CEO score can go negative.** The novice's Q4 settles at −2.24: `final = trait_total +
   modifier_total` and neither engine clamps, while the bands only describe 0–100. `docs/`
   does not state a floor, so none was invented. Decide whether to clamp, and where.
2. **The working-capital ceiling is advisory and overspending pays.** The intermediate
   persona breached it twice and still finished with a bigger company than a version that
   throttled to fit. The expert only pulled ahead once it drew on the credit facility rather
   than cutting the plan. That may be the intended lesson; it is worth calibrating on purpose.
3. **Password resets depend on dashboard state this repo cannot set.** `probe_password_reset_redirect`
   was run against the live project: Supabase honours
   `https://my-elin-frontend.vercel.app/reset-password` and **rejects** the preview-build URL
   this repo's `.env` used to point at, falling back to the project's Site URL — which is set
   to `https://my-elin-frontend.vercel.app/**`, a wildcard pattern rather than a page. Local
   `.env` now points at the production alias. Still outstanding, in the Supabase dashboard:
   set **Site URL** to a real URL (no `/**`), and add `.../reset-password` for production and
   `http://localhost:3000/reset-password` to **Redirect URLs**. The deployed backend's
   `PASSWORD_RESET_REDIRECT_URL` / `CORS_ORIGINS` need the same correction if they still carry
   the preview URL. Note that email delivery is currently switched off in Supabase for
   development, so no reset mail is sent at all; the signed-in change-password screen is the
   flow that works today.

## Conventions worth keeping

- `docs/` is the specification of record. If a coefficient is not there, it does not exist —
  raise `NotImplementedError` rather than guessing, and do not present a guess as authoritative.
- Commit messages describe their own diff. `docs:` only when the diff is docs-only.
- `tests/e2e` is marked `e2e` and hits the real Supabase test schema. Keep the fast suite fast.
