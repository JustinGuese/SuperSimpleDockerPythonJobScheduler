from datetime import datetime
from os import environ

from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

DATABASE_URL = f"postgresql+psycopg2://{environ['POSTGRES_USER']}:{environ['POSTGRES_PASSWORD']}@{environ['POSTGRES_HOST']}:{environ['POSTGRES_PORT']}/{environ['POSTGRES_DB']}"
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
    # echo=True # debugging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency
def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


# class job
class Job(Base):
    __tablename__ = "jobs"
    name = Column(String, unique=True, primary_key=True, index=True, nullable=False)
    repo = Column(String, nullable=False)
    description = Column(String, nullable=True)
    on = Column(Boolean, default=True)
    cron_schedule = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    job_runs = relationship("JobRun", back_populates="job")


# manual pydantic model
class PDJob(BaseModel):
    name: str
    repo: str
    description: str
    on: bool
    cron_schedule: str

    class Config:
        orm_mode = True


class JobRun(Base):
    __tablename__ = "job_runs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_name = Column(String, ForeignKey("jobs.name"), nullable=False)
    status = Column(
        Enum("success", "failed", "running", "pending", name="job_status"),
        nullable=False,
    )
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    logs = Column(String, nullable=True)
    job = relationship("Job", back_populates="job_runs")


# manual pydantic model
class PDJobRun(BaseModel):
    id: int
    job_name: str
    status: str
    start_time: datetime
    end_time: datetime

    class Config:
        orm_mode = True


Base.metadata.create_all(bind=engine)
