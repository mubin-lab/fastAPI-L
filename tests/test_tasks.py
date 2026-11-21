from .conftest import API, create_project, create_task


async def test_task_crud_and_defaults(client, user_a):
    h = user_a["headers"]
    p = await create_project(client, h)
    t = await create_task(client, h, p["id"], "Write docs", due_date="2030-01-31", priority="high")
    assert t["status"] == "todo" and t["priority"] == "high" and t["due_date"] == "2030-01-31"
    assert t["owner_id"] == user_a["user"]["id"]
    got = await client.get(f"{API}/tasks/{t['id']}", headers=h)
    assert got.status_code == 200 and got.json()["title"] == "Write docs"
    assert (await client.delete(f"{API}/tasks/{t['id']}", headers=h)).status_code == 204
    assert (await client.get(f"{API}/tasks/{t['id']}", headers=h)).status_code == 404


async def test_patch_uses_exclude_unset(client, user_a):
    h = user_a["headers"]
    p = await create_project(client, h)
    t = await create_task(client, h, p["id"], "T", description="keep", due_date="2030-01-01")
    r = await client.patch(f"{API}/tasks/{t['id']}", json={"status": "done"}, headers=h)
    assert r.json()["status"] == "done" and r.json()["description"] == "keep" and r.json()["due_date"] == "2030-01-01"
    # explicit null clears a nullable field
    r = await client.patch(f"{API}/tasks/{t['id']}", json={"due_date": None}, headers=h)
    assert r.json()["due_date"] is None and r.json()["status"] == "done"
    # explicit null on a required field is rejected
    assert (await client.patch(f"{API}/tasks/{t['id']}", json={"title": None}, headers=h)).status_code == 422


async def test_task_validation_422(client, user_a):
    h = user_a["headers"]
    p = await create_project(client, h)
    base = {"project_id": p["id"], "title": "x"}
    for bad in ({"title": ""}, {"status": "weird"}, {"priority": "urgent"}, {"due_date": "not-a-date"}):
        r = await client.post(f"{API}/tasks", json={**base, **bad}, headers=h)
        assert r.status_code == 422, bad
    assert (await client.post(f"{API}/tasks", json={"title": "no project"}, headers=h)).status_code == 422


async def test_cannot_create_task_in_foreign_or_missing_project(client, user_a, user_b):
    p = await create_project(client, user_a["headers"])
    r = await client.post(f"{API}/tasks", json={"project_id": p["id"], "title": "x"}, headers=user_b["headers"])
    assert r.status_code == 404
    r = await client.post(f"{API}/tasks", json={"project_id": 9999, "title": "x"}, headers=user_a["headers"])
    assert r.status_code == 404


async def test_isolation_between_users(client, user_a, user_b):
    p = await create_project(client, user_a["headers"])
    t = await create_task(client, user_a["headers"], p["id"])
    hb = user_b["headers"]
    assert (await client.get(f"{API}/tasks/{t['id']}", headers=hb)).status_code == 404
    assert (await client.patch(f"{API}/tasks/{t['id']}", json={"title": "x"}, headers=hb)).status_code == 404
    assert (await client.delete(f"{API}/tasks/{t['id']}", headers=hb)).status_code == 404
    assert (await client.get(f"{API}/tasks", headers=hb)).json()["total"] == 0
    assert (await client.get(f"{API}/tasks", params={"project_id": p["id"]}, headers=hb)).json()["total"] == 0


async def test_admin_reads_all_tasks_but_cannot_edit(client, admin, user_a):
    p = await create_project(client, user_a["headers"])
    t = await create_task(client, user_a["headers"], p["id"])
    ha = admin["headers"]
    assert (await client.get(f"{API}/tasks/{t['id']}", headers=ha)).status_code == 200
    assert (await client.get(f"{API}/tasks", headers=ha)).json()["total"] == 1
    assert (await client.patch(f"{API}/tasks/{t['id']}", json={"title": "x"}, headers=ha)).status_code == 404


async def test_filters_sort_pagination(client, user_a):
    h = user_a["headers"]
    p1 = await create_project(client, h, "P1")
    p2 = await create_project(client, h, "P2")
    await create_task(client, h, p1["id"], "Buy milk", priority="low", due_date="2030-01-10")
    await create_task(client, h, p1["id"], "Write report", priority="high", status="in_progress", due_date="2030-03-01")
    await create_task(client, h, p1["id"], "Deploy", priority="medium", status="done")
    await create_task(client, h, p2["id"], "Milk the cow", priority="high", due_date="2030-02-01")

    def titles(r):
        return [i["title"] for i in r.json()["items"]]

    r = await client.get(f"{API}/tasks", headers=h)
    assert r.json()["total"] == 4
    r = await client.get(f"{API}/tasks", params={"project_id": p2["id"]}, headers=h)
    assert titles(r) == ["Milk the cow"]
    r = await client.get(f"{API}/tasks", params={"status": "done"}, headers=h)
    assert titles(r) == ["Deploy"]
    r = await client.get(f"{API}/tasks", params={"priority": "high", "sort_by": "title", "order": "asc"}, headers=h)
    assert titles(r) == ["Milk the cow", "Write report"]
    r = await client.get(f"{API}/tasks", params={"q": "MILK", "sort_by": "title", "order": "asc"}, headers=h)
    assert titles(r) == ["Buy milk", "Milk the cow"]
    r = await client.get(f"{API}/tasks", params={"due_before": "2030-02-15", "sort_by": "due_date", "order": "asc"}, headers=h)
    assert titles(r) == ["Buy milk", "Milk the cow"]  # tasks without due_date excluded
    r = await client.get(f"{API}/tasks", params={"sort_by": "priority", "order": "desc"}, headers=h)
    assert titles(r)[-1] == "Buy milk" and r.json()["items"][0]["priority"] == "high"
    r = await client.get(f"{API}/tasks", params={"sort_by": "title", "order": "asc", "size": 3, "page": 2}, headers=h)
    assert titles(r) == ["Write report"]
    assert r.json()["total"] == 4 and r.json()["pages"] == 2 and r.json()["size"] == 3


async def test_invalid_query_params_422(client, user_a):
    h = user_a["headers"]
    for params in ({"status": "bogus"}, {"sort_by": "password"}, {"page": 0}, {"size": 0}, {"due_before": "x"}):
        assert (await client.get(f"{API}/tasks", params=params, headers=h)).status_code == 422, params


async def test_old_unversioned_paths_are_gone(client, user_a):
    r = await client.get("/tasks", headers=user_a["headers"])
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
