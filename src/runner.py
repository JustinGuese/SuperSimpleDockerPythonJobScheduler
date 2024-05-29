from datetime import datetime
from time import sleep

from cron_validator import CronValidator

from api.db import Job, JobRun, get_db

db = next(get_db())
allJobs = db.query(Job.name, Job.cron_schedule).all()
while True:
    for jobname, cron in allJobs:
        nowRoundedToMinute = datetime.now().replace(second=0, microsecond=0)
        if CronValidator.match_datetime(cron, nowRoundedToMinute):
            # TODO: start job
            pass
    sleep(60)
