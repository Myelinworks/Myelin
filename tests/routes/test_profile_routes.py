"""`GET /profile` / `PATCH /profile` -- the onboarding-answer settings surface."""

from httpx import AsyncClient

from app.main import app
from app.routes.deps import get_current_user


async def test_profile_starts_empty(client: AsyncClient, current_test_user):
    res = await client.get("/profile")
    assert res.status_code == 200
    body = res.json()
    assert body["user_id"] == str(current_test_user.id)
    assert body["email"] == current_test_user.email
    assert body["first_name"] is None
    assert body["institution"] is None
    assert body["degree"] is None
    assert body["current_year"] is None
    assert body["goals"] == []


async def test_patch_sets_every_field(client: AsyncClient):
    payload = {
        "first_name": "Asha",
        "institution": {"id": "iit-hyderabad", "name": "IIT Hyderabad", "verified": True},
        "degree": "B.Tech / B.E.",
        "current_year": "3rd Year",
        "goals": ["Decision-making", "Leadership"],
    }
    res = await client.patch("/profile", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["first_name"] == "Asha"
    assert body["institution"] == payload["institution"]
    assert body["degree"] == payload["degree"]
    assert body["current_year"] == payload["current_year"]
    assert body["goals"] == payload["goals"]

    # A second read sees the same thing -- the write actually persisted.
    res = await client.get("/profile")
    assert res.json()["first_name"] == "Asha"


async def test_patch_is_a_partial_update(client: AsyncClient):
    await client.patch("/profile", json={"first_name": "Asha", "degree": "BBA"})

    res = await client.patch("/profile", json={"degree": "MBA / PGDM"})
    assert res.status_code == 200
    body = res.json()
    # Left out of this payload -- unchanged, not cleared.
    assert body["first_name"] == "Asha"
    assert body["degree"] == "MBA / PGDM"


async def test_patch_can_clear_a_field_with_null(client: AsyncClient):
    await client.patch("/profile", json={"first_name": "Asha"})

    res = await client.patch("/profile", json={"first_name": None})
    assert res.status_code == 200
    assert res.json()["first_name"] is None


async def test_patch_clearing_institution_resets_verified(client: AsyncClient):
    await client.patch(
        "/profile",
        json={"institution": {"id": "iit-hyderabad", "name": "IIT Hyderabad", "verified": True}},
    )

    res = await client.patch("/profile", json={"institution": None})
    assert res.status_code == 200
    assert res.json()["institution"] is None


async def test_goals_over_the_cap_are_rejected(client: AsyncClient):
    res = await client.patch("/profile", json={"goals": ["a", "b", "c", "d"]})
    assert res.status_code == 422


async def test_profile_requires_authentication(client: AsyncClient) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    res = await client.get("/profile")
    assert res.status_code == 401
