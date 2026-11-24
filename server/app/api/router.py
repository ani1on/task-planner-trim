from fastapi import APIRouter

from .routes.activity import router as activity_router
from .routes.auth import router as auth_router
from .routes.comments import router as comments_router
from .routes.dashboard import router as dashboard_router
from .routes.members import router as members_router
from .routes.notes import router as notes_router
from .routes.projects import router as projects_router
from .routes.realtime import router as realtime_router
from .routes.search import router as search_router
from .routes.tasks import router as tasks_router
from .routes.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(projects_router)
api_router.include_router(members_router)
api_router.include_router(tasks_router)
api_router.include_router(comments_router)
api_router.include_router(notes_router)
api_router.include_router(activity_router)
api_router.include_router(dashboard_router)
api_router.include_router(search_router)
api_router.include_router(users_router)
api_router.include_router(realtime_router)
