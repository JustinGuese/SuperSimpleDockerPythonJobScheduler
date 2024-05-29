import logging
from datetime import datetime
from glob import glob
from os import environ
from pathlib import Path
from subprocess import check_call

from cron_validator import CronValidator
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from api.db import Job, JobRun, PDJobRun, get_db
from api.jobs import dbJobToPDJob, getJobFromDB

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

WORKSPACE = environ.get("WORKSPACE", "/workspace")


def createJobFromRepo(db: Session, giturl: str, branch: str, user: str):
    reponame = giturl.split("/")[-1]
    # check if reponame folder exists in WORKSPACE
    repoLocalPath = Path(WORKSPACE) / reponame
    # git clone or pull
    if not repoLocalPath.exists():
        check_call(["git", "clone", giturl], cwd=WORKSPACE)
    else:
        check_call(["git", "pull"], cwd=repoLocalPath)

    # list all .py files in repoLocalPath/flows/
    pyFlowFiles = glob(str(repoLocalPath / "flows" / "*.py"))
    for file in pyFlowFiles:
        # grab the first line of the file
        with open(file) as f:
            first_line = f.readline()
        # cron: 5 4 * * * # see https://crontab.guru, this always needs to be the first line
        cron = first_line.split(" #")[0].strip().split("cron: ")[1].strip()
        if not CronValidator().is_valid(cron):
            logging.error(f"Invalid cron schedule {cron} in {file}")
            continue
        jobName = file.split("/")[-1].split(".")[0]
        dbJob = db.query(Job).filter(Job.name == jobName).first()
        if not dbJob:
            dbJob = Job(name=jobName, repo=giturl, cron_schedule=cron)
            db.add(dbJob)
        else:
            dbJob.cron_schedule = cron
        dbJob.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(dbJob)
        logging.info(f"Created job {dbJob.name} with cron {dbJob.cron_schedule}")


@router.post("/")
async def gitWebhook(request: Request, db: Session = Depends(get_db)):
    req = await request.json()
    branch = req["ref"].split("/")[-1]
    giturl = req["repository"]["html_url"]
    user = req["pusher"]["name"]
    print(f"Received webhook from {user} on branch {branch} of {giturl}")
    createJobFromRepo(db, giturl, branch, user)
