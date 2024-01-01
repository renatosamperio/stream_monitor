FROM python:3.11.5

ARG SERVICE

RUN apt-get update && \
    apt-get -y install \
        rsync && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /opt/stream_monitor/$SERVICE
COPY ./build/$SERVICE/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

# Copy service files
WORKDIR /opt/stream_monitor/$SERVICE
COPY ./src/$SERVICE/app.py .
COPY ./src/$SERVICE/utilities.py .
COPY ./src/$SERVICE/backuper.py .

COPY ./build/$SERVICE/init /
RUN chmod 755 /init

EXPOSE 5001
WORKDIR /opt/stream_monitor
CMD [ "/init" ]