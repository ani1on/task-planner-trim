from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...api.deps import get_current_user
from ...api.serializers import task_response
from ...database import get_db
from ...models.user import User
from ...schemas.common import MessageResponse
from ...schemas.task import TaskCreate, TaskResponse, TaskUpdate
from ...services.task import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    project_id: int | None = None,
    status_filter: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskResponse]:
    tasks = TaskService(db).list(
        user_id=current_user.id,
        project_id=project_id,
        status=status_filter,
        priority=priority,
        assignee_id=assignee_id,
        search=search,
    )
    return [task_response(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    return task_response(TaskService(db).get(task_id, current_user.id))


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    task = TaskService(db).create(current_user.id, data)
    db.commit()
    return task_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    service = TaskService(db)
    task = service.get(task_id, current_user.id)
    task = service.update(task, current_user.id, data)
    db.commit()
    return task_response(task)


@router.delete("/{task_id}", response_model=MessageResponse)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service = TaskService(db)
    task = service.get(task_id, current_user.id)
    service.soft_delete(task, current_user.id)
    db.commit()
    return MessageResponse(message="Task deleted")
