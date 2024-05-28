from datetime import datetime
from os import environ
from pathlib import Path
from subprocess import PIPE, check_call, run

from api.db import Job, JobRun, PDJobRun, get_db

WORKSPACE = environ.get("WORKSPACE", "/workspace")


def runJob(jobRunId: int, job_name: str):
    db = next(get_db())
    jobRun = db.query(JobRun).filter(JobRun.id == jobRunId).first()
    job = db.query(Job).filter(Job.name == job_name).first()
    if jobRun is None:
        raise Exception("Job Run not found: " + str(jobRunId))
    jobRun.status = "running"
    db.commit()
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
    jobRunId = job.name.lower() + "_" + str(jobRun.id)
    try:
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
    except Exception as e:
        jobRun.status = "failed"
        jobRun.logs = str(e)
        jobRun.end_time = datetime.utcnow()
        db.commit()
        db.refresh(jobRun)
        return PDJobRun.model_validate(jobRun.__dict__) if jobRun else None
    # get logs
    logs = run(
        ["docker", "logs", jobRunId, "-f"],
        stdout=PIPE,
        stderr=PIPE,
        cwd=f"{WORKSPACE}/{reponame}",
    )
    jobRun.status = "success"
    jobRun.logs = logs.stdout.decode("utf-8")
    # Check if the container exited with an error
    container_status = run(
        ["docker", "inspect", "-f", "{{.State.ExitCode}}", jobRunId],
        stdout=PIPE,
        cwd=f"{WORKSPACE}/{reponame}",
    )
    if int(container_status.stdout.decode("utf-8")) != 0:
        jobRun.status = "failed"
        jobRun.logs += container_status.stdout.decode("utf-8").strip()
    jobRun.end_time = datetime.utcnow()
    db.commit()
    db.refresh(jobRun)
    return PDJobRun.model_validate(jobRun.__dict__) if jobRun else None


# if __name__ == "__main__":
#     db = next(get_db())
#     TESTNAME = "exampleFlow"  # errorFlow
#     job = db.query(Job).filter(job.name == TESTNAME).first()
#     if job is None:
#         job = Job(
#             name=TESTNAME,
#             repo="https://github.com/JustinGuese/SuperSimpleDockerPythonJobScheduler-JobTemplate.git",
#             cron_schedule="5 4 * * *",
#         )
#         db.add(job)
#         db.commit()
#         db.refresh(job)
#     print(job)
#     runJob(job)
