FROM python:3.12
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

ARG REQUIRED_PACKAGES="supervisor nginx libnginx-mod-http-js"
ARG OPTIONAL_PACKAGES="vim less curl jq htop strace net-tools iproute2 psmisc"

RUN \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ${REQUIRED_PACKAGES} ${OPTIONAL_PACKAGES} && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

RUN \
    # allow access to circuits on AWS by symlink where the S3 storage is mounted
    # (/sbo) to /gpfs. On k8s, this link will be overlayed w/ the real GPFS
    ln -sf /sbo /gpfs && \
    # create app user
    useradd --create-home --shell /bin/sh -u 1001 app

COPY ./nginx/ /etc/nginx/
COPY ./src/app/ /code/app/
COPY ./logging.yaml /code/logging.yaml
COPY ./supervisord.conf /etc/supervisor/supervisord.conf

ARG PROJECT_PATH
ARG COMMIT_SHA
ENV PROJECT_PATH=${PROJECT_PATH}
ENV COMMIT_SHA=${COMMIT_SHA}
ENV PYTHONPATH=/code

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
