"""Сервис поиска по задачам и проектам."""

from client.api.client import ApiClient
from client.api.mapper import task_view


class SearchService:
    """Ищет объекты через API и возвращает unified-список результатов."""

    def __init__(self, api: ApiClient):
        self.api = api

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Возвращает список найденных объектов с типом."""
        params = {"q": query, "limit": limit}
        raw = self.api.get("/search", params=params) or {}

        results: list[dict] = []

        # Задачи
        for item in raw.get("tasks", []) or []:
            task = task_view(item, {})
            results.append(
                {
                    "type": "tasks",
                    "id": item.get("id"),
                    "title": task.get("title", ""),
                    "name": task.get("title", ""),
                    "project": task.get("project"),
                    "search_text": " ".join(
                        str(value)
                        for value in (
                            task.get("title"),
                            item.get("description"),
                            task.get("project"),
                        )
                        if value
                    ),
                }
            )

        # Проекты
        for item in raw.get("projects", []) or []:
            results.append(
                {
                    "type": "projects",
                    "id": item.get("id"),
                    "title": item.get("name") or item.get("title", ""),
                    "name": item.get("name") or item.get("title", ""),
                    "search_text": " ".join(
                        str(value)
                        for value in (
                            item.get("name"),
                            item.get("title"),
                            item.get("description"),
                        )
                        if value
                    ),
                }
            )

        return results
