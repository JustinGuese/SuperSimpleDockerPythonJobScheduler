from fastapi import Depends, FastAPI, HTTPException, Request

from api.job_runs import router as job_runs_router
from api.jobs import router as jobs_router
from api.webhook import router as webhook_router

app = FastAPI(title="simple job scheduler api", version="0.1.0")
app.include_router(jobs_router)
app.include_router(job_runs_router)
app.include_router(webhook_router)
