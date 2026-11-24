import os


class Config:
    API_URL = os.getenv(
        "TASK_PLANNER_API_URL",
        "https://task-planner-trim.onrender.com",
    )

    API_TIMEOUT = int(
        os.getenv(
            "TASK_PLANNER_API_TIMEOUT",
            "10",
        )
    )
