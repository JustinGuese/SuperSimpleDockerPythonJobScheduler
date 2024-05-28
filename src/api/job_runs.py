from datetime import datetime
from threading import Thread
from typing import List

from cron_validator import CronValidator
from fastapi import APIRouter, Depends, HTTPException, Request

from api.db import JobRun, PDJobRun, get_db
from api.jobs import dbJobToPDJob, getJobFromDB
from runner import runJob

router = APIRouter(prefix="/api/job-runs", tags=["job-runs"])

cv = CronValidator()


@router.get("/", response_model=List[PDJobRun])
def get_job_runs(limit: int = 10, db=Depends(get_db)) -> List[PDJobRun]:
    job_runs = db.query(JobRun).order_by(JobRun.start_time.desc()).limit(limit).all()
    return [PDJobRun.model_validate(job_run.__dict__) for job_run in job_runs]


@router.post("/{job_name}", response_model=PDJobRun)
def create_job_run(job_name: str, db=Depends(get_db)) -> PDJobRun:
    job = getJobFromDB(db, job_name)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    jobRun = JobRun(job_name=job.name, status="pending", start_time=datetime.utcnow())
    db.add(jobRun)
    db.commit()
    db.refresh(jobRun)
    # start runJob in background
    Thread(target=runJob, args=(jobRun.id, job.name)).start()
    return PDJobRun.model_validate(jobRun.__dict__)


@router.get("/{job_run_id}", response_model=PDJobRun)
def get_job_run(job_run_id: int, db=Depends(get_db)) -> PDJobRun:
    job_run = db.query(JobRun).filter(JobRun.id == job_run_id).first()
    if job_run is None:
        raise HTTPException(status_code=404, detail="Job Run not found")
    return PDJobRun.model_validate(job_run.__dict__)
