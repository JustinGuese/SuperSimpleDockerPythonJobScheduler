FROM python:3.11-slim
RUN apt update && apt install -y {{SYSTEM_DEPS}}
RUN pip install --no-cache-dir {{PIP_DEPS}}
COPY ./flows/ /app
WORKDIR /app