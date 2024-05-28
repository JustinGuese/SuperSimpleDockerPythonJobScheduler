from datetime import datetime
from os import environ
from pathlib import Path
from subprocess import PIPE, check_call, run

from api.db import Job, JobRun, PDJobRun, get_db

WORKSPACE = environ.get("WORKSPACE", "/workspace")


def runJob(job: Job):
    reponame = job.repo.split("/")[-1].replace(".git", "")
    # git clone the repo into workspace
    # check if folder exists
    if not Path(f"{WORKSPACE}/{reponame}").exists():
        check_call(["git", "clone", job.repo, f"{WORKSPACE}/{reponame}"])
    else:
        check_call(["git", "pull"], cwd=f"{WORKSPACE}/{reponame}")
    # copy standard Dockerfile to workspace
    check_call(["cp", "Dockerfile", f"{WORKSPACE}/{reponame}/"])
    # read sys-requirements.txt from repo if exists
    sys_req_file = Path(f"{WORKSPACE}/{reponame}/sys-requirements.txt")
    sys_req = []
    if sys_req_file.exists():
        with open(sys_req_file, "r") as f:
            sys_req = f.readlines()
    # read requirements.txt from repo if exists
    req_file = Path(f"{WORKSPACE}/{reponame}/requirements.txt")
    req = []
    if req_file.exists():
        with open(req_file, "r") as f:
            req = f.readlines()
    # replace in dockerfile
    with open(f"{WORKSPACE}/{reponame}/Dockerfile", "r") as f:
        dockerfile = f.read()
    dockerfile = dockerfile.replace("{{SYSTEM_DEPS}}", " ".join(sys_req))
    dockerfile = dockerfile.replace("{{PIP_DEPS}}", " ".join(req))
    with open(f"{WORKSPACE}/{reponame}/Dockerfile", "w") as f:
        f.write(dockerfile)

    # build docker image
    check_call(
        ["docker", "build", "-t", reponame.lower(), "."],
        cwd=f"{WORKSPACE}/{reponame}",
    )
    # run docker container
    jobRun = JobRun(job_name=job.name, status="running", start_time=datetime.utcnow())
    db = next(get_db())
    db.add(jobRun)
    db.commit()
    db.refresh(jobRun)
    jobRunId = job.name.lower() + "_" + str(jobRun.id)
    check_call(
        [
            "docker",
            "run",
            "--name",
            jobRunId,
            reponame.lower(),
            "python",
            job.name + ".py",
        ],
        cwd=f"{WORKSPACE}/{reponame}",
    )
    # get logs
    logs = run(
        ["docker", "logs", jobRunId, "-f"],
        stdout=PIPE,
        cwd=f"{WORKSPACE}/{reponame}",
    )
    if logs.returncode == 0:
        jobRun.status = "success"
        jobRun.logs = logs.stdout.decode("utf-8")
    else:
        jobRun.status = "failed"
        jobRun.logs = logs.stderr.decode("utf-8")
    jobRun.end_time = datetime.utcnow()
    db.commit()
    print("logs: ", jobRun.logs)


if __name__ == "__main__":
    db = next(get_db())
    job = db.query(Job).filter(Job.name == "exampleFlow").first()
    if job is None:
        job = Job(
            name="exampleFlow",
            repo="https://github.com/JustinGuese/SuperSimpleDockerPythonJobScheduler-JobTemplate.git",
            cron_schedule="5 4 * * *",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
    print(job)
    runJob(job)
