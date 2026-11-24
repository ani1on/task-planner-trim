from ..models.project import Project
from ..models.task import Task
from ..schemas.project import ProjectResponse
from ..schemas.task import TaskResponse


def task_response(task: Task) -> TaskResponse:
    return TaskResponse.model_validate(task)


def project_response(
    project: Project,
    *,
    role: str | None = None,
    progress: tuple[int, int] | None = None,
) -> ProjectResponse:
    data = ProjectResponse.model_validate(project)
    update: dict = {}

    if role is not None:
        update["role"] = role

    if progress is not None:
        total, done = progress
        update["tasks_total"] = total
        update["tasks_done"] = done
        update["progress"] = int(done / total * 100) if total else 0

    return data.model_copy(update=update)
