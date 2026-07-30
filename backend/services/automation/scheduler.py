from typing import Any, Dict, Callable


class TaskScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, func: Callable, interval_seconds: int) -> str:
        job_id = f"job_{len(self.jobs) + 1}"
        self.jobs.append({"id": job_id, "func": func.__name__, "interval": interval_seconds})
        return job_id
