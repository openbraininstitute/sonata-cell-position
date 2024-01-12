FROM python:3.10
SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

WORKDIR /code

# RUN mkdir -p ~/.ssh && ssh-keyscan -t rsa bbpgitlab.epfl.ch >> ~/.ssh/known_hosts

COPY ./requirements.txt /code/requirements.txt

RUN \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

ARG INSTALL_DEBUG_TOOLS
RUN \
    if [[ "${INSTALL_DEBUG_TOOLS}" == "true" ]]; then \
        SYSTEM_DEBUG_TOOLS="vim less curl jq htop strace net-tools iproute2" && \
        PYTHON_DEBUG_TOOLS="py-spy memory-profiler" && \
        echo "Installing tools for profiling and inspection..." && \
        apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ${SYSTEM_DEBUG_TOOLS} && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/* && \
        pip install --no-cache-dir --upgrade ${PYTHON_DEBUG_TOOLS} ; \
    fi

COPY ./src/app /code/app
COPY ./logging.yaml /code/logging.yaml

ARG PROJECT_PATH
ARG COMMIT_SHA
ENV PROJECT_PATH=${PROJECT_PATH}
ENV COMMIT_SHA=${COMMIT_SHA}

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8050", "--proxy-headers", "--log-config", "/code/logging.yaml"]
