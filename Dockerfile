FROM public.ecr.aws/lambda/python:3.8

ARG pypi_index

COPY requirements.txt .

RUN  pip3 install --no-cache-dir --extra-index-url ${pypi_index} -r requirements.txt --target "${LAMBDA_TASK_ROOT}" && \
    rm requirements.txt

COPY src ${LAMBDA_TASK_ROOT}

CMD [ "app.handler" ]
