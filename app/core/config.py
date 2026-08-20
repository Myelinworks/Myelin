import json
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Myelin Backend"
    environment: str = "development"

    database_url: str
    redis_url: str

    # `NoDecode` on every list field: without it pydantic-settings JSON-decodes the raw env
    # string before validation runs, so a plain `a,b,c` -- the only thing a hosting dashboard's
    # env-var box invites you to type -- raises SettingsError and the process dies at import,
    # before a single log line. `_split_csv` accepts both that and a JSON array.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Vercel mints a distinct origin per deployment (`<project>-<hash>-<scope>.vercel.app`), so an
    # enumerated allow-list goes stale the next time the frontend deploys and every browser call
    # starts failing preflight. This regex covers the whole project's deployment family in one
    # entry. Anchored at both ends -- an unanchored pattern would match any host that merely
    # *contains* the project name, e.g. `evil-myelin-frontend.attacker.com`.
    cors_origin_regex: str = ""

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwks_url: str = ""

    # The browser origin this API's frontend is served from. Used to derive any URL that has
    # to point *back* at the frontend -- currently just the password-reset landing page.
    frontend_url: str = "http://localhost:3000"

    # Where Supabase redirects after a user clicks the password-reset email link (the
    # frontend's own reset-password page). Passed as `redirect_to` on `/auth/v1/recover`.
    # Left blank on purpose: `password_reset_redirect` below derives it from `frontend_url`
    # rather than letting a blank value mean "send no redirect_to at all", which is how reset
    # links silently ended up on the Supabase project's Site URL (a 404) instead of this page.
    password_reset_redirect_url: str = ""

    # The valid-role universe, kept in config so a new role is an env change, not a code
    # change. Which of these roles get cross-ownership read access is a business rule, not
    # a config knob -- see authorization_service.INSTRUCTOR_ROLES.
    app_roles: Annotated[list[str], NoDecode] = ["student", "instructor", "admin"]

    @property
    def password_reset_redirect(self) -> str:
        """The `redirect_to` every recovery email must carry -- never empty.

        Supabase only honours a `redirect_to` that its own Auth -> URL Configuration ->
        Redirect URLs allow-list matches; anything else (including *no* `redirect_to`) is
        silently replaced with the project's Site URL. That silent substitution is what turned
        every reset link into a 404, so this always resolves to a real page and
        `probe_password_reset_redirect` checks at startup that Supabase actually accepts it.
        """
        return self.password_reset_redirect_url or f"{self.frontend_url.rstrip('/')}/reset-password"

    @field_validator("cors_origins", "app_roles", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Accept `a,b,c` or `["a","b","c"]`. Empty entries are dropped so a trailing comma
        can't produce an empty-string origin, which CORS would then try to match."""
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if stripped.startswith("["):
            return json.loads(stripped)
        return [item.strip() for item in stripped.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
