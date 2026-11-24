import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from client.api.client import ApiClient
from client.ui.components.project_card import ProjectCard
from client.ui.pages.dashboard_page import DashboardPage
from client.ui.pages.projects_page import ProjectsPage
from client.ui.pages.tasks_page import TasksPage


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _api():
    return ApiClient("http://127.0.0.1:1")


def _projects():
    return [
        {
            "id": 1,
            "name": "Task Planner",
            "description": "Планировщик задач",
            "color": "blue",
            "status": "active",
            "done": 0,
            "total": 0,
            "members": [],
        },
        {
            "id": 2,
            "name": "Документация",
            "description": "Описание схемы данных",
            "color": "purple",
            "status": "active",
            "done": 0,
            "total": 0,
            "members": [],
        },
        {
            "id": 3,
            "name": "Инфраструктура",
            "description": "Настройка CI",
            "color": "teal",
            "status": "active",
            "done": 0,
            "total": 0,
            "members": [],
        },
    ]


def _tasks():
    tasks = [
        ("Собрать каркас интерфейса", 1, "in_progress", "high"),
        ("Продумать схему базы данных", 1, "done", "medium"),
        ("Подключить авторизацию", 1, "review", "critical"),
        ("Описать REST API задач", 2, "todo", "low"),
        ("Настроить CI для тестов", 3, "todo", "medium"),
    ]
    return [
        {
            "id": task_id,
            "title": title,
            "project_id": project_id,
            "project": next(
                project["name"] for project in _projects()
                if project["id"] == project_id
            ),
            "description": "",
            "status": status,
            "priority": priority,
            "due": "",
            "due_at": None,
            "done": status == "done",
        }
        for task_id, (title, project_id, status, priority)
        in enumerate(tasks, start=1)
    ]


def test_tasks_page_filters_project_and_shows_all(qapp):
    page = TasksPage(api=_api())
    page._set_tasks({
        "views": _tasks(),
        "models": {},
        "projects": _projects(),
    })
    assert {task["id"] for task in page.all_tasks} == {1, 2, 3, 4, 5}

    page.project_combo.setCurrentIndex(page.project_combo.findData(2))
    assert {card.task["id"] for card in page._task_cards.values()} == {4}

    page.project_combo.setCurrentIndex(0)
    assert {card.task["id"] for card in page._task_cards.values()} == {
        1, 2, 3, 4, 5
    }


def test_dashboard_task_cards_cannot_be_edited(qapp):
    page = DashboardPage(api=_api())
    page.content_layout.addLayout(page._build_today(_tasks()[:3]))
    card = next(iter(page._task_cards.values()))

    assert card.more_button.isHidden()
    assert all(button.isHidden() for button in card.panel_buttons.values())

    card.activated.emit(card._task_id())
    card.toggle_editor()

    assert card.editor.isHidden()


def test_tasks_page_searches_and_filters_by_text(qapp):
    page = TasksPage(api=_api())
    page._set_tasks({
        "views": _tasks(),
        "models": {},
        "projects": _projects(),
    })

    page.search_input.setText("REST")
    assert set(page._task_cards) == {4}


def test_projects_page_searches_by_name_and_description(qapp):
    page = ProjectsPage(api=_api())
    page._render({"views": _projects(), "models": {}})

    page.search_input.setText("схемы данных")
    assert set(page._project_cards) == {2}


def test_project_card_keeps_status_dropdown_without_archive_or_progress_buttons(qapp):
    card = ProjectCard({
        "id": 1,
        "name": "Проект",
        "status": "active",
    })

    assert card.status_combo.findData("archived") >= 0
    button_texts = [button.text().casefold() for button in card.findChildren(QPushButton)]
    assert not any("архив" in text or "прогресс" in text for text in button_texts)


