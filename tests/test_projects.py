from .conftest import API, create_project, create_task


async def test_project_crud(client, user_a):
    h = user_a["headers"]
    p = await create_project(client, h, "Website", description="desc")
    assert p["archived"] is False and p["owner_id"] == user_a["user"]["id"]
    assert (await client.get(f"{API}/projects/{p['id']}", headers=h)).json()["name"] == "Website"
    r = await client.patch(f"{API}/projects/{p['id']}", json={"archived": True}, headers=h)
    assert r.json()["archived"] is True and r.json()["name"] == "Website"  # untouched field preserved
    assert (await client.delete(f"{API}/projects/{p['id']}", headers=h)).status_code == 204
    assert (await client.get(f"{API}/projects/{p['id']}", headers=h)).status_code == 404


async def test_project_validation_422(client, user_a):
    h = user_a["headers"]
    assert (await client.post(f"{API}/projects", json={"name": ""}, headers=h)).status_code == 422
    assert (await client.post(f"{API}/projects", json={}, headers=h)).status_code == 422
    p = await create_project(client, h)
    r = await client.patch(f"{API}/projects/{p['id']}", json={"name": None}, headers=h)
    assert r.status_code == 422


async def test_projects_require_auth(client):
    assert (await client.get(f"{API}/projects")).status_code == 401


async def test_project_list_pagination_search_filter(client, user_a):
    h = user_a["headers"]
    for i in range(5):
        await create_project(client, h, f"Alpha {i}")
    await create_project(client, h, "Beta", archived=False)
    p = await create_project(client, h, "Gamma")
    await client.patch(f"{API}/projects/{p['id']}", json={"archived": True}, headers=h)
    r = await client.get(f"{API}/projects", params={"size": 4}, headers=h)
    body = r.json()
    assert body["total"] == 7 and len(body["items"]) == 4 and body["pages"] == 2
    r = await client.get(f"{API}/projects", params={"q": "alpha"}, headers=h)
    assert r.json()["total"] == 5
    r = await client.get(f"{API}/projects", params={"archived": True}, headers=h)
    assert [x["name"] for x in r.json()["items"]] == ["Gamma"]
    assert (await client.get(f"{API}/projects", params={"size": 1000}, headers=h)).status_code == 422
    assert (await client.get(f"{API}/projects", params={"q": "%"}, headers=h)).json()["total"] == 0  # escaped


async def test_isolation_between_users(client, user_a, user_b):
    p = await create_project(client, user_a["headers"], "Secret")
    hb = user_b["headers"]
    assert (await client.get(f"{API}/projects/{p['id']}", headers=hb)).status_code == 404
    assert (await client.patch(f"{API}/projects/{p['id']}", json={"name": "x"}, headers=hb)).status_code == 404
    assert (await client.delete(f"{API}/projects/{p['id']}", headers=hb)).status_code == 404
    assert (await client.get(f"{API}/projects", headers=hb)).json()["total"] == 0


async def test_admin_reads_all_but_cannot_modify_others(client, admin, user_a):
    p = await create_project(client, user_a["headers"], "Mine")
    ha = admin["headers"]
    assert (await client.get(f"{API}/projects/{p['id']}", headers=ha)).status_code == 200
    assert (await client.get(f"{API}/projects", headers=ha)).json()["total"] == 1
    assert (await client.patch(f"{API}/projects/{p['id']}", json={"name": "x"}, headers=ha)).status_code == 404
    assert (await client.delete(f"{API}/projects/{p['id']}", headers=ha)).status_code == 404


async def test_deleting_project_deletes_its_tasks(client, user_a):
    h = user_a["headers"]
    p = await create_project(client, h)
    t = await create_task(client, h, p["id"])
    await client.delete(f"{API}/projects/{p['id']}", headers=h)
    assert (await client.get(f"{API}/tasks/{t['id']}", headers=h)).status_code == 404
