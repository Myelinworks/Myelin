import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._examples import example


class RegisterRequest(BaseModel):
    """`POST /auth/register` -- proxies straight to Supabase Auth's signup API. Password hashing
    and session-token signing are entirely Supabase's; this backend never implements either."""

    model_config = ConfigDict(json_schema_extra={"example": example("auth_register_request")})

    email: str
    password: str


class LoginRequest(BaseModel):
    """`POST /auth/login` -- proxies to Supabase Auth's password grant."""

    model_config = ConfigDict(json_schema_extra={"example": example("auth_login_request")})

    email: str
    password: str


class AuthResponse(BaseModel):
    """The session returned by both `/auth/register` and `/auth/login`. Send `access_token` as
    `Authorization: Bearer <access_token>` on every subsequent request."""

    model_config = ConfigDict(json_schema_extra={"example": example("auth_login_response")})

    access_token: str = Field(description="The Supabase-issued JWT -- send as a Bearer token on every other request.")
    refresh_token: str | None = None
    user_id: uuid.UUID = Field(description="The Supabase auth user id -- becomes this user's `owner_id` on any company they create.")
    email: str
