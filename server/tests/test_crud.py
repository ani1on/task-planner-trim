from fastapi.testclient import TestClient

from server.main import app


def create_project(client: TestClient, name: str = "Тестовый проект") -> dict:
    response = client.post("/projects", json={"name": name})

    assert response.status_code == 201, response.text

    return response.json()


def create_task(
    client: TestClient,
    project_id: int,
    title: str = "Тестовая задача",
) -> dict:
    response = client.post(
        "/tasks",
        json={"project_id": project_id, "title": title},
    )

    assert response.status_code == 201, response.text

    return response.json()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_projects_require_auth() -> None:
    client = TestClient(app)

    assert client.get("/projects").status_code in (401, 403)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def test_project_crud(auth_client: TestClient) -> None:
    created = auth_client.post(
        "/projects",
        json={"name": "Диплом", "color": "violet"},
    )

    assert created.status_code == 201

    project = created.json()

    assert project["name"] == "Диплом"
    assert project["status"] == "active"

    listed = auth_client.get("/projects")

    assert listed.status_code == 200
    assert any(p["id"] == project["id"] for p in listed.json())

    fetched = auth_client.get(f"/projects/{project['id']}")

    assert fetched.status_code == 200

    updated = auth_client.patch(
        f"/projects/{project['id']}",
        json={"name": "Диплом v2"},
    )

    assert updated.status_code == 200
    assert updated.json()["name"] == "Диплом v2"
    assert updated.json()["color"] == "violet"

    archived = auth_client.post(f"/projects/{project['id']}/archive")

    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    deleted = auth_client.delete(f"/projects/{project['id']}")

    assert deleted.status_code == 200
    assert auth_client.get(f"/projects/{project['id']}").status_code == 404


def test_project_delete_cascades_to_tasks_and_comments(
    auth_client: TestClient,
) -> None:
    project = create_project(auth_client)
    task = create_task(auth_client, project["id"])
    comment_response = auth_client.post(
        "/comments",
        json={"task_id": task["id"], "content": "Комментарий"},
    )
    assert comment_response.status_code == 201, comment_response.text
    comment = comment_response.json()

    deleted = auth_client.delete(f"/projects/{project['id']}")

    assert deleted.status_code == 200, deleted.text
    assert auth_client.get(f"/projects/{project['id']}").status_code == 404
    assert auth_client.get(f"/tasks/{task['id']}").status_code == 404
    assert auth_client.get(f"/comments/{comment['id']}").status_code == 404


def test_project_not_found(auth_client: TestClient) -> None:
    response = auth_client.get("/projects/999999")

    assert response.status_code == 404
    assert response.json()["code"] == "project_not_found"


def test_project_isolation(
    auth_client: TestClient,
    other_client: TestClient,
) -> None:
    project = create_project(auth_client)

    assert other_client.get(f"/projects/{project['id']}").status_code == 404

    assert (
        other_client.patch(
            f"/projects/{project['id']}",
            json={"name": "hack"},
        ).status_code
        == 404
    )

    assert other_client.delete(f"/projects/{project['id']}").status_code == 404

    ids = [p["id"] for p in other_client.get("/projects").json()]

    assert project["id"] not in ids


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def test_task_crud(auth_client: TestClient) -> None:
    project = create_project(auth_client)

    created = auth_client.post(
        "/tasks",
        json={
            "project_id": project["id"],
            "title": "Сделать UI",
            "priority": "high",
        },
    )

    assert created.status_code == 201

    task = created.json()

    assert task["status"] == "todo"
    assert task["completed_at"] is None

    done = auth_client.patch(
        f"/tasks/{task['id']}",
        json={"status": "done"},
    )

    assert done.status_code == 200
    assert done.json()["completed_at"] is not None

    reopened = auth_client.patch(
        f"/tasks/{task['id']}",
        json={"status": "todo"},
    )

    assert reopened.json()["completed_at"] is None

    listed = auth_client.get(
        "/tasks",
        params={"project_id": project["id"]},
    )

    assert any(t["id"] == task["id"] for t in listed.json())

    deleted = auth_client.delete(f"/tasks/{task['id']}")

    assert deleted.status_code == 200
    assert auth_client.get(f"/tasks/{task['id']}").status_code == 404

    ids = [t["id"] for t in auth_client.get("/tasks").json()]

    assert task["id"] not in ids


def test_task_isolation(
    auth_client: TestClient,
    other_client: TestClient,
) -> None:
    project = create_project(auth_client)
    task = create_task(auth_client, project["id"])

    assert other_client.get(f"/tasks/{task['id']}").status_code == 404

    assert (
        other_client.patch(
            f"/tasks/{task['id']}",
            json={"title": "hack"},
        ).status_code
        == 404
    )

    response = other_client.post(
        "/tasks",
        json={"project_id": project["id"], "title": "x"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "project_not_found"


def test_invalid_status_returns_422(auth_client: TestClient) -> None:
    project = create_project(auth_client)

    response = auth_client.post(
        "/tasks",
        json={
            "project_id": project["id"],
            "title": "x",
            "status": "поехали",
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


def test_comment_crud(auth_client: TestClient) -> None:
    project = create_project(auth_client)
    task = create_task(auth_client, project["id"])

    created = auth_client.post(
        "/comments",
        json={"task_id": task["id"], "content": "Первый комментарий"},
    )

    assert created.status_code == 201

    comment = created.json()

    updated = auth_client.patch(
        f"/comments/{comment['id']}",
        json={"content": "Обновлено"},
    )

    assert updated.json()["content"] == "Обновлено"

    listed = auth_client.get(
        "/comments",
        params={"task_id": task["id"]},
    )

    assert len(listed.json()) == 1

    assert auth_client.delete(f"/comments/{comment['id']}").status_code == 200
    assert auth_client.get(f"/comments/{comment['id']}").status_code == 404


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


def test_note_crud(auth_client: TestClient) -> None:
    created = auth_client.post(
        "/notes",
        json={"title": "Идея", "content": "Текст заметки"},
    )

    assert created.status_code == 201

    note = created.json()

    pinned = auth_client.patch(
        f"/notes/{note['id']}",
        json={"is_pinned": True},
    )

    assert pinned.json()["is_pinned"] is True

    assert any(n["id"] == note["id"] for n in auth_client.get("/notes").json())

    assert auth_client.delete(f"/notes/{note['id']}").status_code == 200
    assert auth_client.get(f"/notes/{note['id']}").status_code == 404


def test_note_foreign_project(
    auth_client: TestClient,
    other_client: TestClient,
) -> None:
    project = create_project(auth_client)

    response = other_client.post(
        "/notes",
        json={
            "title": "x",
            "content": "y",
            "project_id": project["id"],
        },
    )

    assert response.status_code == 404
    assert response.json()["code"] == "project_not_found"


# ---------------------------------------------------------------------------
# Profile & Settings
# ---------------------------------------------------------------------------


def test_update_profile(auth_client: TestClient) -> None:
    response = auth_client.patch("/users/me", json={"nick_name": "new_nick"})

    assert response.status_code == 200
    assert response.json()["nick_name"] == "new_nick"

    assert auth_client.get("/auth/me").json()["nick_name"] == "new_nick"


def test_update_profile_duplicate_nickname(
    auth_client: TestClient,
    other_client: TestClient,
) -> None:
    other_nick_name = other_client.get("/auth/me").json()["nick_name"]

    response = auth_client.patch(
        "/users/me",
        json={"nick_name": other_nick_name},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "nickname_already_exists"


def test_settings_flow(auth_client: TestClient) -> None:
    fetched = auth_client.get("/users/me/settings")

    assert fetched.status_code == 200
    assert fetched.json()["theme"] in ("light", "dark")

    updated = auth_client.patch(
        "/users/me/settings",
        json={"theme": "dark"},
    )

    assert updated.status_code == 200
    assert updated.json()["theme"] == "dark"

    again = auth_client.get("/users/me/settings")

    assert again.json()["theme"] == "dark"


def test_settings_invalid_theme(auth_client: TestClient) -> None:
    response = auth_client.patch("/users/me/settings", json={"theme": "neon"})

    assert response.status_code == 422
