FROM python
RUN pip install fastapi uvicorn requests

ADD . .

RUN chmod +x run.sh
CMD ./run.sh