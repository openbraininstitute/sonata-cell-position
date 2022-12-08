FROM python:3.9

WORKDIR /code

# RUN mkdir -p ~/.ssh && ssh-keyscan -t rsa bbpgitlab.epfl.ch >> ~/.ssh/known_hosts

COPY ./requirements.txt /code/requirements.txt
COPY ./external/randomaccessbuffer-1.0.0.tar.gz /code/external/ram.tar.gz

RUN \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --upgrade /code/external/ram.tar.gz && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./src/app /code/app
COPY ./logging.yaml /code/logging.yaml

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--log-config", "/code/logging.yaml"]
