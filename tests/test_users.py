from .conftest import API, login


async def test_get_and_patch_me(client, user_a):
    r = await client.patch(f"{API}/users/me", json={"full_name": "Alice"}, headers=user_a["headers"])
    assert r.status_code == 200 and r.json()["full_name"] == "Alice"
    assert (await client.get(f"{API}/users/me", headers=user_a["headers"])).json()["full_name"] == "Alice"


async def test_me_cannot_change_role(client, user_a):
    r = await client.patch(f"{API}/users/me", json={"role": "admin"}, headers=user_a["headers"])
    assert r.status_code == 200 and r.json()["role"] == "user"


async def test_admin_endpoints_forbidden_for_normal_user(client, user_a):
    h = user_a["headers"]
    assert (await client.get(f"{API}/users", headers=h)).status_code == 403
    assert (await client.get(f"{API}/users/1", headers=h)).status_code == 403
    assert (await client.patch(f"{API}/users/1", json={"role": "admin"}, headers=h)).status_code == 403
    assert (await client.delete(f"{API}/users/1", headers=h)).status_code == 403
    assert (await client.get(f"{API}/users")).status_code == 401


async def test_admin_list_search_pagination(client, admin, user_a, user_b):
    r = await client.get(f"{API}/users", headers=admin["headers"])
    body = r.json()
    assert body["total"] == 3 and body["page"] == 1 and len(body["items"]) == 3
    r = await client.get(f"{API}/users", params={"size": 2, "page": 2}, headers=admin["headers"])
    assert len(r.json()["items"]) == 1 and r.json()["pages"] == 2
    r = await client.get(f"{API}/users", params={"q": "a@example"}, headers=admin["headers"])
    assert [u["email"] for u in r.json()["items"]] == ["a@example.com"]
    r = await client.get(f"{API}/users", params={"role": "admin"}, headers=admin["headers"])
    assert r.json()["total"] == 1


async def test_admin_get_user_and_404(client, admin, user_a):
    r = await client.get(f"{API}/users/{user_a['user']['id']}", headers=admin["headers"])
    assert r.status_code == 200 and r.json()["email"] == "a@example.com"
    assert (await client.get(f"{API}/users/9999", headers=admin["headers"])).status_code == 404


async def test_admin_sets_role_and_active_flag(client, admin, user_a):
    uid = user_a["user"]["id"]
    r = await client.patch(f"{API}/users/{uid}", json={"role": "admin"}, headers=admin["headers"])
    assert r.json()["role"] == "admin"
    # the (still valid) access token now passes the admin guard because role is read from the DB
    assert (await client.get(f"{API}/users", headers=user_a["headers"])).status_code == 200
    r = await client.patch(f"{API}/users/{uid}", json={"is_active": False}, headers=admin["headers"])
    assert r.json()["is_active"] is False
    assert (await login(client, "a@example.com")).status_code == 403


async def test_admin_cannot_deactivate_or_demote_self(client, admin):
    me = (await client.get(f"{API}/users/me", headers=admin["headers"])).json()
    r = await client.delete(f"{API}/users/{me['id']}", headers=admin["headers"])
    assert r.status_code == 409
    r = await client.patch(f"{API}/users/{me['id']}", json={"role": "user"}, headers=admin["headers"])
    assert r.status_code == 409


async def test_invalid_role_is_422(client, admin, user_a):
    r = await client.patch(f"{API}/users/{user_a['user']['id']}", json={"role": "root"}, headers=admin["headers"])
    assert r.status_code == 422
