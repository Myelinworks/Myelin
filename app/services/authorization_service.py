"""Phase 13: "may this user act on this run at all" -- deliberately separate from
`app/services/run_service.py`'s gatekeeper, which answers "is this move legal in this game
state." Both functions here are pure/sync field comparisons on an already-loaded `Company`;
neither takes a session nor calls into `app/engines/*`/`RunFacts`, which is what keeps
identity structurally incapable of leaking into the gatekeeper or the pure engine.

Every write route in `routes/deps.py`/`routes/company.py` calls `require_owner` (or the
broader `require_read_access` for reads) strictly before it calls `require_move` -- 404 (does
it exist) -> 403 (is it yours) -> 409 (is this move legal right now).
"""

from app.models.company import Company
from app.services.auth_service import CurrentUser

# The read-only cross-ownership roles (task brief: "an instructor viewing, not editing, a
# student's run"). A business rule, not a config knob -- see Settings.app_roles for the
# broader valid-role universe this is drawn from.
INSTRUCTOR_ROLES = {"instructor", "admin"}


class NotPermittedError(Exception):
    """Raised when an authenticated user isn't allowed to act on/view a company/run they
    don't own. Distinct from `IllegalMoveError` (legality of a move on a run the user *does*
    own) and from a 404 (the resource doesn't exist at all) -- `main.py` maps this to its own
    403 `not_permitted` envelope."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def require_owner(company: Company, user: CurrentUser) -> None:
    """Write-path check: the acting user must be this company's owner."""
    if company.owner_id != user.id:
        raise NotPermittedError(f"user {user.id} does not own company {company.id}")


def require_read_access(company: Company, user: CurrentUser) -> None:
    """Read-path check: owner OR instructor/admin role may read. Broader than `require_owner`
    by design -- the one seam where cross-ownership is allowed, and only for reads."""
    if company.owner_id == user.id:
        return
    if user.role in INSTRUCTOR_ROLES:
        return
    raise NotPermittedError(f"user {user.id} may not view company {company.id}")
