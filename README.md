# [pipeline_name]

An example Airflow pipeline using Docker and GitLab CI. Make sure to document the following questions, as well as review the guide below.

The *Data Owner* is responsible for the data within their perimeter in terms of its collection, protection and quality. The *Data Steward* would then be responsible for referencing and aggregating the information, definitions and any other business needs to simplify the discovery and understanding of these assets.

# FAQ

**Q. Who is the Data Owner?** \
**A.** [answer]

**Q. Who is the Data Steward?** \
**A.** [answer]

**Q. What is the Department supporting this?** \
**A.** [answer]

**Q. Who requested this?** \
**A.** [answer]

**Q. Why was this requested?** \
**A.** [answer]

**Q. What is it used for?** \
**A.** [answer]

**Q. Why is this valuable?** \
**A.** [answer]

**Q. Where does the data come from?** \
**A.** [answer]

**Q. Where does it go?** \
**A.** [answer]

**Q. What could cause this to break?** \
**A.** [answer]

**Q. What challenges were faced, if any?** \
**A.** [answer]

# Setup

## Environment

* Ensure you have [Docker](https://docs.docker.com/engine/) setup locally (e.g. in [WSL](https://docs.microsoft.com/en-us/windows/wsl/install-win10)). See the PBLabs Wiki for some [useful post-setup steps](https://wiki.pitchbooklabs.com/doc/docker-wZlypffCLN).
* In your environment (e.g. WSL, VM, etc.) set the `PYPI_INDEX` variable to `https://nexus.pitchbooklabs.com/repository/pypi-internal/simple` to allow installation of Python packages from our internal registry (the variable will be passed through to the Docker build automatically).
* Setup your local environment to use our internal Python package registry ([instructions](https://wiki.pitchbooklabs.com/doc/internal-pypi-setup-IA3jQgj9Rz)).

# Usage

## Pipeline/Docker

To build a new pipeline using this template, do the following:

1. Develop pipeline code (e.g. in a local environment, Jupyter Notebook, Docker, etc.). You can simply execute `docker compose up --build` and a hosted container using environment will start. This will start a Jupyter notebook in the background. Click the URL to login.
2. Create a new project for pipeline in [airflow-automation/pipelines](https://git.pitchbookdata.com/business-intelligence/airflow-automation/pipelines), using the automation script. It sets a lot of defaults and does automated pipeline step creation.
3. Copy contents of this repo to new project.
4. Add pipeline code (i.e. replace [pipeline.py](pipeline/pipeline.py) with one or more files containing your code).
5. Add Python requirements to [requirements.txt](requirements.txt) this would be for anything standard by pip that you need in a pipeline (e.g. `numpy`, `pandas`, `bi_connection_s3`, `bi_connection_snowflake`, etc.).
6. Set necessary base image in the [Dockerfile](Dockerfile) (e.g. [python/3.7-slim, python/3.8, etc.](https://hub.docker.com/_/python)).
7. Add any necessary environment variables to the [Dockerfile](Dockerfile). Many of the standard environment variables already exist or will be prepopulated by the DAG executions.
8. Set command in [docker-compose.yaml](docker-compose.yaml) to run the desired script.
9. Test pipeline by running `docker compose up --build`.
10. Once container has been built and started you should see the Docker image running jupyter.
11. If you want to run the pipeline manually or test some changes in the container, type `docker ps` and find the container running jupyter. Then execute `docker exec -it <MY_CONTAINTER_ID> /bin/bash` to open up a terminal in the machine. From there simply navigate to `/core/pipeline` and execute `python pipeline.py` to run the pipeline.
12. Alternatively, you can connect to a running container via [VSCode](https://code.visualstudio.com/docs/remote/containers-tutorial), if you prefer to use an IDE.
13. When you are done developing exit of out Jupyter via `CTRL+C`, then the container should exit status 0 when it's finished.

## Credentials

### AWS

Make sure your have AWS SSO authentication setup, as your local AWS creds will be passed into the running container with a volume.

### Other

Make sure you setup a `${CREDS_PATH}` environment variable to allow `docker compose` to add credentials for local development via volumes:

1. You can host it anywhere on your machine.
2. Formatting for credentials is `/creds/bi_creds_<MY_CONNECTION_NAME>/bi_secrets_<MY_CONNECTION_NAME>.yaml`. Prefixing is important here.

## CI/CD

### Initial Setup

To setup the [GitLab CI](https://docs.gitlab.com/ee/ci/) pipeline (for automated Docker image builds and pushes), do the following:

1. Create an [ECR repo](https://us-west-2.console.aws.amazon.com/ecr/repositories?region=us-west-2).
2. Update [gitlab-ci.yml](.gitlab-ci.yml) to set the `IMAGE_NAME` variable (note: this must match the ECR repo name).
3. Merge code to the master branch.
4. The release pipeline will build and push a Docker image to the ECR repo you created with the tag you specified, where it is now ready to be referenced in a DAG. The image will be available at `542960883369.dkr.ecr.us-west-2.amazonaws.com/[ecr-repo]:[tag]`. Following the Docker push, the DAGs image file will be updated with the new image tag.

### Pipeline Updates

1. Make changes.
2. Update the pipeline [version](version.txt).
3. Merge changes to the master branch.
4. The release pipeline will build and push a Docker image with the tag you specified. Following the Docker push, the DAGs image file will be updated with the new image tag.

## DAGs

Once the container has been pushed you're ready to create an [Airflow DAG](https://airflow.apache.org/docs/apache-airflow/stable/concepts.html#dags):

1. Create a new DAG file in the [Kubernetes DAGs repo](https://git.pitchbookdata.com/business-intelligence/orchestration/dags/business-intelligence-dags) using the template [dag.py](dags/dag.py).
2. Commit to dev branch and test in [Airflow dev](https://airflow-dev.pitchbookbi.com).
3. Merge to master branch and run in [Airflow prod](https://airflow.pitchbookbi.com).
