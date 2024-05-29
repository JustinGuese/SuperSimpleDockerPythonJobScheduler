from cron_validator import CronValidator
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.db import JobRun, PDJobRun, get_db
from api.jobs import dbJobToPDJob, getJobFromDB

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


@router.post("/")
def gitWebhook(request: Request, db: Session = Depends(get_db)):
    req = request.json()
    print("got git webhook:")
    print(req)