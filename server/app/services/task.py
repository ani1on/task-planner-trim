from sqlalchemy.orm import Session

from ..core.errors import AppException
from ..core.time import utcnow
from ..models.task import Task
from ..realtime import events, project_room, publish
from ..repositories.project import ProjectRepository
from ..repositories.task import TaskRepository
from ..schemas.task import TaskCreate, TaskUpdate
from .access import AccessService
from .activity import ActivityService


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tasks = TaskRepository(db)
        self.projects = ProjectRepository(db)
        self.access = AccessService(db)
        self.activity = ActivityService(db)

    def list(
        self,
        user_id: int,
        project_id: int | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee_id: int | None = None,
        search: str | None = None,
    ) -> list[Task]:
        return self.tasks.list_for_user(
            user_id=user_id,
            project_id=project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
            search=search,
        )

    def get(
        self,
        task_id: int,
        user_id: int,
    ) -> Task:
        task = self.tasks.get_for_user(task_id, user_id)

        if task is None:
            raise AppException(
                status_code=404,
                detail="Task not found",
                code="task_not_found",
            )

        return task

    def create(
        self,
        user_id: int,
        data: TaskCreate,
    ) -> Task:
        project = self.projects.get_for_user(data.project_id, user_id)

        if project is None:
            raise AppException(
                status_code=404,
                detail="Project not found",
                code="project_not_found",
            )

        self.access.require_role(data.project_id, user_id, "member")

        if data.assignee_id is not None:
            self._check_assignee(data.project_id, data.assignee_id)

        task = Task(
            project_id=data.project_id,
            created_by_id=user_id,
            assignee_id=data.assignee_id,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            start_at=data.start_at,
            due_at=data.due_at,
            position=data.position,
        )

        if task.status == "done":
            task.completed_at = utcnow()

        task = self.tasks.create(task)

        self.activity.log(
            user_id=user_id,
            action="task_created",
            entity_type="task",
            entity_id=task.id,
            project_id=task.project_id,
            task_id=task.id,
            new_values={
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
            },
        )

        publish(
            project_room(task.project_id),
            events.TASK_CREATED,
            {
                "id": task.id,
                "project_id": task.project_id,
                "status": task.status,
                "assignee_id": task.assignee_id,
            },
        )

        return task

    def update(
        self,
        task: Task,
        user_id: int,
        data: TaskUpdate,
    ) -> Task:
        self.access.require_role(task.project_id, user_id, "member")

        changes = data.model_dump(exclude_unset=True)

        if "assignee_id" in changes and changes["assignee_id"] is not None:
            self._check_assignee(task.project_id, changes["assignee_id"])

        old_values = {
            field: getattr(task, field)
            for field in changes
        }

        for field, value in changes.items():
            setattr(task, field, value)

        if "status" in changes:
            if task.status == "done":
                task.completed_at = utcnow()
            else:
                task.completed_at = None

        self.db.flush()

        self.activity.log(
            user_id=user_id,
            action="task_updated",
            entity_type="task",
            entity_id=task.id,
            project_id=task.project_id,
            task_id=task.id,
            old_values=old_values,
            new_values=changes,
        )

        if "assignee_id" in changes:
            publish(
                project_room(task.project_id),
                events.TASK_ASSIGNED,
                {
                    "id": task.id,
                    "project_id": task.project_id,
                    "assignee_id": task.assignee_id,
                },
            )

        publish(
            project_room(task.project_id),
            events.TASK_UPDATED,
            {
                "id": task.id,
                "project_id": task.project_id,
                "status": task.status,
                "priority": task.priority,
                "assignee_id": task.assignee_id,
            },
        )

        return task

    def soft_delete(
        self,
        task: Task,
        user_id: int,
    ) -> None:
        self.access.require_role(task.project_id, user_id, "member")

        task.deleted_at = utcnow()

        self.db.flush()

        self.activity.log(
            user_id=user_id,
            action="task_deleted",
            entity_type="task",
            entity_id=task.id,
            project_id=task.project_id,
            task_id=task.id,
            old_values={"title": task.title},
        )

        publish(
            project_room(task.project_id),
            events.TASK_DELETED,
            {
                "id": task.id,
                "project_id": task.project_id,
            },
        )

    def _check_assignee(
        self,
        project_id: int,
        assignee_id: int,
    ) -> None:
        if self.access.role(project_id, assignee_id) is None:
            raise AppException(
                status_code=400,
                detail="Assignee is not a project member",
                code="assignee_not_project_member",
            )

