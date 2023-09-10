#!/bin/bash

echo "Running message dispatcher..."
python /opt/stream_monitor/src/app.py &
sleep 2

echo "Running torrent watchdog..."
python /opt/stream_monitor/src/qbitorrent.py &


