from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routes import allocations, auth, company, cx, endgame, finance, marketing, product, quarter, run, sales
from app.routes.deps import NotAuthenticatedError
from app.services.authorization_service import NotPermittedError
from app.services.run_service import IllegalMoveError

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Deterministic CEO decision-simulation engine. A run belongs to the authenticated user "
        "who started it; every write is checked for identity (owner-or-instructor), then "
        "legality (the single gatekeeper), before it touches anything. See "
        "`docs/frontend-integration-guide.md` in the repo for the full lifecycle walkthrough --"
        " this reference documents each endpoint in isolation; the guide covers the flow."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Registration/login -- proxies to Supabase Auth. Not run-scoped."},
        {"name": "company", "description": "Start a run, open quarters, read current state."},
        {"name": "run", "description": "The single rich run-state read -- poll this between every write."},
        {"name": "allocations", "description": "The 22-line spend model + the crisis-response line. The primary write surface."},
        {"name": "quarter", "description": "Lock a quarter, read its report, read the leaderboard."},
        {"name": "endgame", "description": "The Q4 endgame preview and strategic decision."},
        {"name": "finance", "description": "Legacy per-decision pipeline -- not part of the primary allocation flow."},
        {"name": "marketing", "description": "Legacy per-decision pipeline -- not part of the primary allocation flow."},
        {"name": "product", "description": "Legacy per-decision pipeline -- not part of the primary allocation flow."},
        {"name": "sales", "description": "Legacy per-decision pipeline -- not part of the primary allocation flow."},
        {"name": "cx", "description": "Legacy per-decision pipeline -- not part of the primary allocation flow."},
    ],
)


@app.exception_handler(NotAuthenticatedError)
async def not_authenticated_handler(_request: Request, _exc: NotAuthenticatedError) -> JSONResponse:
    """401: the request carries no usable identity at all -- distinct from `not_permitted`
    (we know who you are, you just can't touch this) and from `illegal_move` (you can touch
    this, just not right now)."""
    return JSONResponse(status_code=401, content={"error": "not_authenticated"})


@app.exception_handler(NotPermittedError)
async def not_permitted_handler(_request: Request, exc: NotPermittedError) -> JSONResponse:
    """403: authenticated, but not this run's owner (write) or not owner-or-instructor
    (read). Distinct from `illegal_move`'s 409 and from a plain 404 -- a client can tell
    "not your run" apart from "not a legal move right now" apart from "doesn't exist"."""
    return JSONResponse(status_code=403, content={"error": "not_permitted", "reason": exc.reason})


@app.exception_handler(IllegalMoveError)
async def illegal_move_handler(_request: Request, exc: IllegalMoveError) -> JSONResponse:
    """Phase 12: the one shape every illegal-move refusal takes, from whichever route raised it --
    `error`/`reason` for a human, `allowed_moves` for a client to decide what to show next without
    parsing prose. 409: the request is well-formed, it just conflicts with the run's current state,
    the same convention `routes/deps.py::get_open_quarter` already established for "quarter locked".
    """
    return JSONResponse(
        status_code=409,
        content={
            "error": "illegal_move",
            "attempted_move": exc.move.value,
            "reason": exc.reason,
            "allowed_moves": sorted(m.value for m in exc.allowed),
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Operations and People workspaces have no rules config yet (see README) -- not wired
# until operations_rules.json/people_rules.json exist, rather than shipping routers that
# can never accept a real decision.
app.include_router(auth.router)
app.include_router(company.router)
app.include_router(finance.router)
app.include_router(marketing.router)
app.include_router(product.router)
app.include_router(sales.router)
app.include_router(cx.router)
app.include_router(allocations.router)
app.include_router(quarter.router)
app.include_router(endgame.router)
app.include_router(run.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
