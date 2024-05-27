from fastapi import Depends, FastAPI, HTTPException, Request

from api.jobs import router as jobs_router

app = FastAPI(title="simple job scheduler api", version="0.1.0")
app.include_router(jobs_router)
