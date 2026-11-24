from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.main import app


def create_project(client: TestClient, name: str = "Тестовый проект") -> dict:
    response = client.post("/projects", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def create_task(
    client: TestClient,
    project_id: int,
    title: str = "Тестовая задача",
    **extra: object,
) -> dict:
    response = client.post(
        "/tasks",
        json={"project_id": project_id, "title": title, **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_token(client: TestClient) -> str:
    return client.headers["Authorization"].split(" ", 1)[1]


def test_project_members_flow(
    auth_client: TestClient,
    other_client: TestClient,
) -> None:
    project = create_project(auth_client)
    other = other_client.get("/auth/me").json()

    members = auth_client.get(f"/projects/{project['id']}/members")
    assert members.status_code == 200
    assert [member["role"] for member in members.json()] == ["owner"]

    invited = auth_client.post(
        f"/projects/{project['id']}/members",
        json={"email": other["email"], "role": "viewer"},
    )
    assert invited.status_code == 201, invited.text
    assert invited.json()["user_id"] == other["id"]
    assert invited.json()["role"] == "viewer"

    assert other_client.get(f"/projects/{project['id']}").status_code == 200
    forbidden = other_client.post(
        "/tasks",
        json={"project_id": project["id"], "title": "Недоступная задача"},
    )
    assert forbidden.status_code == 403

    promoted = auth_client.patch(
        f"/projects/{project['id']}/members/{other['id']}",
        json={"role": "member"},
    )
    assert promoted.status_code == 200
    create_task(other_client, project["id"], "Задача участника")

    removed = auth_client.delete(
        f"/projects/{project['id']}/members/{other['id']}"
    )
    assert removed.status_code == 200
    assert other_client.get(f"/projects/{project['id']}").status_code == 404


def test_dashboard(auth_client: TestClient) -> None:
    project = create_project(auth_client, "Проект дашборда")
    task = create_task(auth_client, project["id"], "Задача для дашборда")
    auth_client.patch(f"/tasks/{task['id']}", json={"status": "done"})

    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["total_projects"] == 1
    assert data["stats"]["total"] == 1
    assert data["stats"]["done"] == 1
    assert data["projects"][0]["progress"] == 100


def test_search_returns_tasks_projects_and_notes(auth_client: TestClient) -> None:
    project = create_project(auth_client, "Космический проект")
    create_task(auth_client, project["id"], "Запустить ракету")
    auth_client.post(
        "/notes",
        json={"title": "Заметка о ракете", "content": "Топливо"},
    )

    response = auth_client.get("/search", params={"q": "ракет"})
    assert response.status_code == 200
    data = response.json()
    assert any(task["title"] == "Запустить ракету" for task in data["tasks"])
    assert any(note["title"] == "Заметка о ракете" for note in data["notes"])
    assert data["projects"] == []

    by_project = auth_client.get("/search", params={"q": "Космический"})
    assert [item["id"] for item in by_project.json()["projects"]] == [
        project["id"]
    ]


def test_activity_log(auth_client: TestClient) -> None:
    project = create_project(auth_client, "Активный проект")
    task = create_task(auth_client, project["id"], "Задача с историей")

    response = auth_client.get("/activity", params={"project_id": project["id"]})
    assert response.status_code == 200
    actions = [entry["action"] for entry in response.json()]
    assert "task_created" in actions
    assert "project_created" in actions

    by_task = auth_client.get("/activity", params={"task_id": task["id"]}).json()
    assert all(entry["task_id"] == task["id"] for entry in by_task)


def test_websocket_ping_and_join_project(auth_client: TestClient) -> None:
    project = create_project(auth_client)
    with auth_client.websocket_connect(
        f"/ws?token={auth_token(auth_client)}"
    ) as websocket:
        websocket.send_json({"action": "ping"})
        assert websocket.receive_json()["event"] == "pong"
        websocket.send_json(
            {"action": "join_project", "project_id": project["id"]}
        )
        response = websocket.receive_json()
        assert response["event"] == "joined"
        assert response["payload"]["project_id"] == project["id"]


def test_websocket_rejects_foreign_project(
    auth_client: TestClient,
    other_client: TestClient,
) -> None:
    project = create_project(auth_client)
    with other_client.websocket_connect(
        f"/ws?token={auth_token(other_client)}"
    ) as websocket:
        websocket.send_json(
            {"action": "join_project", "project_id": project["id"]}
        )
        response = websocket.receive_json()
        assert response["event"] == "error"
        assert response["payload"]["detail"] == "Project access denied"


def test_websocket_requires_valid_token() -> None:
    client = TestClient(app)
    try:
        with client.websocket_connect("/ws?token=invalid") as websocket:
            websocket.receive_json()
    except WebSocketDisconnect:
        pass
    else:
        raise AssertionError("Invalid WebSocket token was accepted")


def test_removed_feature_routes_are_not_exposed(auth_client: TestClient) -> None:
    for path in ("/events", "/reminders", "/notifications", "/tags", "/checklists"):
        assert auth_client.get(path).status_code == 404
