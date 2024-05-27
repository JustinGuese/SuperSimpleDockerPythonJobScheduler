from datetime import datetime
from typing import List

from cron_validator import CronValidator
from fastapi import APIRouter, Depends, HTTPException, Request

from api.db import Job, JobRun, PDJob, PDJobRun, get_db

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

cv = CronValidator()


def isValidCron(cron: str) -> bool:
    try:
        cv.parse(cron)
        return True
    except ValueError:
        return False


def dbJobToPDJob(job: Job) -> PDJob:
    return PDJob.model_validate(job.__dict__) if job else None


## basic crud for job
@router.get("/", response_model=list[PDJob])
def get_jobs(db=Depends(get_db)) -> list[PDJob]:
    jobs = db.query(Job).all()
    return [PDJob.model_validate(job.__dict__) for job in jobs]


def getJobFromDB(db, job_name: str) -> Job:
    job = db.query(Job).filter(Job.name == job_name).first()
    return job


@router.get("/{job_name}", response_model=PDJob)
def get_job(job_name: str, db=Depends(get_db)) -> PDJob:
    job = getJobFromDB(db, job_name)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return dbJobToPDJob(job)


@router.post("/", response_model=PDJob)
def create_job(job: PDJob, db=Depends(get_db)) -> PDJob:
    # check if job exists
    dbJob = getJobFromDB(db, job.name)
    if dbJob is not None:
        raise HTTPException(status_code=400, detail="Job already exists")
    # check cron
    if job.cron_schedule and not isValidCron(job.cron_schedule):
        raise HTTPException(
            status_code=400, detail="Invalid cron schedule: " + job.cron_schedule
        )
    dbJob = Job(**job.model_dump())
    db.add(dbJob)
    db.commit()
    db.refresh(dbJob)
    return dbJobToPDJob(dbJob)


@router.put("/", response_model=PDJob)
def update_job(job: PDJob, db=Depends(get_db)) -> PDJob:
    dbJob = getJobFromDB(db, job.name)
    if dbJob is None:
        raise HTTPException(status_code=404, detail="Job not found")
    # check cron
    if job.cron_schedule and not isValidCron(job.cron_schedule):
        raise HTTPException(
            status_code=400, detail="Invalid cron schedule: " + job.cron_schedule
        )
    # dbJob.name = job.name
    dbJob.description = job.description
    dbJob.on = job.on
    dbJob.cron_schedule = job.cron_schedule
    dbJob.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(dbJob)
    return dbJobToPDJob(dbJob)


@router.delete("/{job_name}", response_model=PDJob)
def delete_job(job_name: str, db=Depends(get_db)) -> PDJob:
    job = getJobFromDB(db, job_name)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return dbJobToPDJob(job)
