FROM python:3.12
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

# create the app user with the same id used for bbpsbok8sonatacells. See:
# https://bbpgitlab.epfl.ch/cs/kubernetes/flux2-admin/-/blob/3b6fea5/kyverno/gpfs-policies.yml#L499
ARG APP_USER_ID=905632

ARG REQUIRED_PACKAGES="supervisor nginx libnginx-mod-http-js"
ARG OPTIONAL_PACKAGES="vim less curl jq htop strace net-tools iproute2 psmisc"

RUN \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ${REQUIRED_PACKAGES} ${OPTIONAL_PACKAGES} && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN \
    # allow access to circuits on AWS by symlink where the S3 storage is mounted
    # (/sbo) to /gpfs. On k8s, this link will be overlayed w/ the real GPFS
    ln -sf /sbo/data/project /gpfs && \
    useradd --create-home --shell /bin/sh -u $APP_USER_ID app

COPY ./nginx/ /etc/nginx/
COPY ./supervisord.conf /etc/supervisor/supervisord.conf

USER app
WORKDIR /code
ENV PATH="/home/app/.local/bin:$PATH"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

COPY --chown=app:app ./requirements.txt /code/requirements.txt

RUN \
    pip install --user --upgrade pip setuptools wheel && \
    pip install --user --upgrade -r /code/requirements.txt && \
    echo -e 'alias ll="ls -l"\nalias la="ls -lA"' >> ~/.bash_aliases

COPY --chown=app:app ./src/app/ /code/app/
COPY --chown=app:app ./logging.yaml /code/logging.yaml

ARG PROJECT_PATH
ARG COMMIT_SHA
ENV PROJECT_PATH="${PROJECT_PATH}"
ENV COMMIT_SHA="${COMMIT_SHA}"
ENV PYTHONPATH=/code

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
