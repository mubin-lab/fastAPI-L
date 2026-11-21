import jwt
import pytest

from app.core.config import settings
from app.core.security import ALGORITHM

from .conftest import API, PASSWORD, login, make_user, register


async def test_register_login_me(client):
    r = await register(client, "New@Example.com")
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@example.com" and body["role"] == "user" and "hashed_password" not in body
    tokens = (await login(client, "new@example.com")).json()
    assert tokens["token_type"] == "bearer" and tokens["refresh_token"]
    me = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "new@example.com"


async def test_register_duplicate_is_409(client):
    await register(client)
    r = await register(client)
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize("password", ["short1A", "alllowercase123", "ALLUPPERCASE123", "NoDigitsHereAtAll"])
async def test_weak_password_is_422(client, password):
    r = await register(client, password=password)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert r.json()["error"]["details"][0]["field"].endswith("password")


async def test_invalid_email_is_422(client):
    assert (await register(client, "not-an-email")).status_code == 422


async def test_login_wrong_password_and_unknown_user_are_401(client):
    await register(client)
    r1 = await login(client, password="WrongPassw0rd!")
    r2 = await login(client, "ghost@example.com")
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["error"]["message"] == r2.json()["error"]["message"]


async def test_protected_route_requires_token(client):
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"
    r = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


async def test_refresh_rotation_and_reuse_detection(client):
    u = await make_user(client)
    old = u["tokens"]["refresh_token"]
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": old})
    assert r.status_code == 200
    new = r.json()["refresh_token"]
    assert new != old

    # Reusing the rotated (revoked) token is rejected AND revokes the whole family.
    reuse = await client.post(f"{API}/auth/refresh", json={"refresh_token": old})
    assert reuse.status_code == 401 and "reuse" in reuse.json()["error"]["message"].lower()
    after = await client.post(f"{API}/auth/refresh", json={"refresh_token": new})
    assert after.status_code == 401


async def test_access_token_cannot_be_used_as_refresh_and_vice_versa(client):
    u = await make_user(client)
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": u["tokens"]["access_token"]})
    assert r.status_code == 401
    r = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {u['tokens']['refresh_token']}"})
    assert r.status_code == 401 and "token type" in r.json()["error"]["message"].lower()


async def test_access_token_claims(client):
    u = await make_user(client)
    claims = jwt.decode(u["tokens"]["access_token"], settings.secret_key, algorithms=[ALGORITHM])
    assert {"sub", "roles", "exp", "iat", "jti", "type"} <= claims.keys()
    assert claims["type"] == "access" and claims["roles"] == ["user"]


async def test_expired_and_forged_tokens_rejected(client):
    u = await make_user(client)
    uid = u["user"]["id"]
    expired = jwt.encode({"sub": str(uid), "type": "access", "roles": ["user"], "iat": 1, "exp": 2, "jti": "x"},
                         settings.secret_key, algorithm=ALGORITHM)
    forged = jwt.encode({"sub": str(uid), "type": "access", "roles": ["admin"], "iat": 1, "exp": 9999999999,
                         "jti": "x"}, "x" * 40, algorithm=ALGORITHM)
    for tok in (expired, forged):
        r = await client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 401


async def test_logout_revokes_refresh_token(client):
    u = await make_user(client)
    rt = u["tokens"]["refresh_token"]
    assert (await client.post(f"{API}/auth/logout", json={"refresh_token": rt})).status_code == 204
    assert (await client.post(f"{API}/auth/refresh", json={"refresh_token": rt})).status_code == 401


async def test_logout_all_revokes_every_session(client):
    u = await make_user(client)
    second = (await login(client)).json()
    r = await client.post(f"{API}/auth/logout-all", headers=u["headers"])
    assert r.status_code == 204
    for rt in (u["tokens"]["refresh_token"], second["refresh_token"]):
        assert (await client.post(f"{API}/auth/refresh", json={"refresh_token": rt})).status_code == 401


async def test_change_password(client):
    u = await make_user(client)
    bad = await client.post(f"{API}/auth/change-password", headers=u["headers"],
                            json={"current_password": "nope", "new_password": "BrandNewPassw0rd"})
    assert bad.status_code == 401
    ok = await client.post(f"{API}/auth/change-password", headers=u["headers"],
                           json={"current_password": PASSWORD, "new_password": "BrandNewPassw0rd"})
    assert ok.status_code == 204
    assert (await login(client)).status_code == 401
    assert (await login(client, password="BrandNewPassw0rd")).status_code == 200
    # old refresh tokens died with the password change
    r = await client.post(f"{API}/auth/refresh", json={"refresh_token": u["tokens"]["refresh_token"]})
    assert r.status_code == 401


async def test_deactivated_user_cannot_login(client, admin):
    u = await make_user(client)
    r = await client.delete(f"{API}/users/{u['user']['id']}", headers=admin["headers"])
    assert r.status_code == 204
    assert (await login(client)).status_code == 403
    assert (await client.get(f"{API}/auth/me", headers=u["headers"])).status_code == 403
