FROM python:3.11-slim
RUN mkdir -p /app/api/
RUN apt update && apt install -y git docker.io && apt clean
RUN pip install poetry
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root
COPY ./src/api/*.py /app/api/
COPY ./src/*.py /app/
COPY ./src/Dockerfile /app/
CMD ["uvicorn", "app:app", "--host", "0.0.0.0"]