from cron_validator import CronValidator
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.db import JobRun, PDJobRun, get_db
from api.jobs import dbJobToPDJob, getJobFromDB

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


@router.post("/")
async def gitWebhook(request: Request, db: Session = Depends(get_db)):
    req = await request.json()
    branch = req["ref"].split("/")[-1]
    giturl = req["repository"]["html_url"]
    user = req["pusher"]["name"]
    print(f"Received webhook from {user} on branch {branch} of {giturl}")
