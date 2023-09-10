FROM python:3.11.5

WORKDIR /opt/stream_monitor/config
COPY ./config/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /opt/stream_monitor/src
COPY ./src/app.py .
COPY ./src/qbitorrent.py .
COPY ./src/runner.py .

WORKDIR /opt/stream_monitor/bin
COPY ./bin/run.sh .

WORKDIR /opt/stream_monitor
CMD [ "bash", "/opt/stream_monitor/bin/run.sh" ]