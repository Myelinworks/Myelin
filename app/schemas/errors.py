"""The refusal envelopes every run-scoped route can return, as real OpenAPI response schemas --
not left as undocumented 4xx. `main.py`'s exception handlers are the runtime source of truth for
these three shapes (`not_authenticated`/`not_permitted`/`illegal_move`); the models here exist so
FastAPI's generated spec (and any client generated from it) knows their fields ahead of time,
distinct from a plain 404/409 and from each other.

The `_RESPONSES` dicts below are composed onto route decorators via `responses=`, chosen per route
to match what that route can *actually* raise -- e.g. `lock_quarter` never raises `IllegalMoveError`
(it bypasses the gatekeeper; `run_quarter` is its own idempotent guard), so it does not carry
`WRITE_RESPONSES`'s 409 entry.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._examples import example


class NotAuthenticatedResponse(BaseModel):
    """401 -- no usable Bearer token was presented (missing, malformed, expired, or the
    signature didn't verify against Supabase's JWKS). The client should send the user to login.
    """

    model_config = ConfigDict(json_schema_extra={"example": example("error_not_authenticated")})

    error: Literal["not_authenticated"] = Field(description='Always the literal string "not_authenticated".')


class NotPermittedResponse(BaseModel):
    """403 -- the caller is authenticated, but is not this run's owner (every write) or not
    the owner-or-an-instructor/admin (every read). Distinct from `illegal_move`: this is about
    *who* is asking, never about the run's current state.
    """

    model_config = ConfigDict(json_schema_extra={"example": example("error_not_permitted")})

    error: Literal["not_permitted"] = Field(description='Always the literal string "not_permitted".')
    reason: str = Field(description="Human-readable explanation naming the user and company involved.")


class IllegalMoveResponse(BaseModel):
    """409 -- the gatekeeper's envelope (`app/engines/run_state.py`). The caller is authenticated
    and permitted, but the requested move isn't legal in this run's *current state* (e.g.
    submitting a crisis allocation outside the crisis quarter, or opening a quarter before the
    prior one is locked). `allowed_moves` is exactly `GET .../run`'s `legal_moves` at the moment
    of the attempt -- a client can re-render its UI from this field alone, without a second request.
    """

    model_config = ConfigDict(json_schema_extra={"example": example("error_illegal_move")})

    error: Literal["illegal_move"] = Field(description='Always the literal string "illegal_move".')
    attempted_move: str = Field(description="The `Move` enum value the client attempted.")
    reason: str = Field(description="Human-readable explanation of why that move isn't legal right now.")
    allowed_moves: list[str] = Field(
        description="Every `Move` value that IS legal right now, sorted alphabetically."
    )


class NotFoundResponse(BaseModel):
    """The plain `{\"detail\": ...}` shape FastAPI's own `HTTPException` produces. Used for 404
    (the company/quarter doesn't exist at all) and for the handful of route-specific 409s that are
    NOT the gatekeeper's `illegal_move` envelope (e.g. "no report before the quarter is locked",
    "this quarter is already locked; decisions are immutable") -- ordering conflicts specific to
    one route's own read/write guard, not a `Move` the single gatekeeper evaluated.
    """

    model_config = ConfigDict(json_schema_extra={"example": example("error_not_found")})

    detail: str = Field(description="Human-readable explanation of what wasn't found or why the request conflicts.")


AUTH_401 = {401: {"model": NotAuthenticatedResponse, "description": "Not authenticated -- no valid Bearer token."}}
PERMISSION_403 = {
    403: {"model": NotPermittedResponse, "description": "Authenticated, but not permitted for this company/run."}
}
NOT_FOUND_404 = {404: {"model": NotFoundResponse, "description": "The company or quarter does not exist."}}
ILLEGAL_MOVE_409 = {
    409: {
        "model": IllegalMoveResponse,
        "description": "Well-formed and permitted, but not a legal move in the run's current state.",
    }
}
PLAIN_CONFLICT_409 = {
    409: {
        "model": NotFoundResponse,
        "description": "A route-specific ordering conflict (e.g. quarter not locked yet, or already "
        "locked) -- not the gatekeeper's illegal_move envelope.",
    }
}

# Every read route (GET): can 401, can 403 (not owner-or-instructor), can 404 (doesn't exist).
READ_RESPONSES = {**AUTH_401, **PERMISSION_403, **NOT_FOUND_404}

# Every write route that goes through the gatekeeper (POST allocations/endgame/quarters): also
# carries the illegal_move 409.
WRITE_RESPONSES = {**AUTH_401, **PERMISSION_403, **NOT_FOUND_404, **ILLEGAL_MOVE_409}

# Read routes with their own extra, route-specific 409 (report/endgame-preview "not ready yet").
READ_RESPONSES_WITH_PLAIN_CONFLICT = {**READ_RESPONSES, **PLAIN_CONFLICT_409}

# create_company: nothing exists yet to be forbidden or not-found on -- just needs a caller.
CREATE_ONLY_RESPONSES = {**AUTH_401}
