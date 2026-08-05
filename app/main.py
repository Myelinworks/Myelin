from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routes import allocations, company, cx, endgame, finance, marketing, product, quarter, run, sales
from app.services.run_service import IllegalMoveError

settings = get_settings()

app = FastAPI(title=settings.app_name)


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
