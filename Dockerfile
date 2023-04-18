FROM python:3.10

WORKDIR /code

# RUN mkdir -p ~/.ssh && ssh-keyscan -t rsa bbpgitlab.epfl.ch >> ~/.ssh/known_hosts

COPY ./requirements.txt /code/requirements.txt

RUN \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./src/app /code/app
COPY ./logging.yaml /code/logging.yaml

ARG PROJECT_PATH
ARG COMMIT_SHA
ENV PROJECT_PATH=${PROJECT_PATH}
ENV COMMIT_SHA=${COMMIT_SHA}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--log-config", "/code/logging.yaml"]
