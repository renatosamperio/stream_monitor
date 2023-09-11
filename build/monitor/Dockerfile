FROM python:3.11.5

ARG SERVICE

WORKDIR /opt/stream_monitor/$SERVICE
COPY ./build/$SERVICE/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

# Copy service files
WORKDIR /opt/stream_monitor/$SERVICE
COPY ./src/$SERVICE/qbitorrent.py .
COPY ./src/$SERVICE/runner.py .
COPY ./src/$SERVICE/utilities.py .

COPY ./build/$SERVICE/init /
RUN chmod 755 /init

WORKDIR /opt/stream_monitor
CMD [ "/init" ]