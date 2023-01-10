# Base image to use (swap out if you need to use another Python version (e.g. 2.7, 3.6, 3.9, etc.)
FROM python:3.8-slim

LABEL maintainer="Isaiah Morgan isaiah.morgan@pitchbook.com" \
      version="1.0.0"

# create the pipe user
RUN useradd -r -m -U pipeuser

# Argument to enable installing PBLabs/BI Python packages
ARG pypi_index

# SET LOCAL as the environment, this will change via Airflow environment variable injection
ENV ORCHESTRATOR_ENV=local

WORKDIR /core

# Copy requirements first so that we don't have to reinstall dependencies for every code change
COPY --chown=pipeuser:pipeuser requirements.txt /core

# Python package installs
RUN pip install --no-cache-dir --extra-index-url ${pypi_index} -r requirements.txt && \
    rm requirements.txt

# Copy all code into container, currently exclude notebook in .dockerignore
COPY --chown=pipeuser:pipeuser core/ /core/

# change to the pipe user
USER pipeuser
