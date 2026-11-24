import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from client.api.models import Member
from client.core.realtime import RealtimeClient
from client.services.auth import AuthService
from client.themes.manager import ThemeManager
from client.ui.components.task_card import TaskCard
from client.ui.crud_actions import TaskActionsMixin
from client.ui.main_window import MainWindow


def _app():
    return QApplication.instance() or QApplication([])


def test_main_window_contains_only_selected_pages(monkeypatch):
    app = _app()

    class FakeApi:
        base_url = "http://127.0.0.1:1"

    auth = AuthService(FakeApi())
    auth.user = {"id": 1, "nick_name": "User", "email": "user@example.com"}
    monkeypatch.setattr(MainWindow, "navigate_to", lambda self, _key: None)

    window = MainWindow(FakeApi(), auth, ThemeManager(app))

    assert set(window.pages) == {
        "dashboard",
        "tasks",
        "kanban",
        "projects",
        "settings",
    }
    assert set(window.sidebar.buttons) == set(window.pages)


def test_task_comment_shows_author_nickname():
    app = _app()

    class FakeApi:
        def get(self, path, params=None):
            assert path == "/comments"
            return [{
                "id": 3,
                "task_id": 8,
                "author_id": 5,
                "content": "Комментарий",
            }]

    class FakeProjectService:
        def members(self, project_id):
            assert project_id == 2
            return [
                Member(
                    id=1,
                    project_id=2,
                    user_id=5,
                    role="member",
                    nick_name="Автор",
                )
            ]

    class Actions(TaskActionsMixin):
        pass

    card = TaskCard({"id": 8, "project_id": 2, "title": "Задача"})
    page = Actions()
    page.api = FakeApi()
    page.task_service = object()
    page.project_service = FakeProjectService()
    page.user_id = 1
    page._task_cards = {8: card}

    page.open_task_panel(8, "comments")
    app.processEvents()

    labels = [label.text() for label in card.findChildren(QLabel)]
    assert "Автор" in labels


def test_realtime_client_can_join_and_leave_projects():
    _app()
    realtime = RealtimeClient("http://localhost")
    sent = []
    realtime.socket.sendTextMessage = sent.append

    realtime.join_project(12)
    realtime.leave_project(12)

    assert sent == [
        '{"action": "join_project", "project_id": 12}',
        '{"action": "leave_project", "project_id": 12}',
    ]
