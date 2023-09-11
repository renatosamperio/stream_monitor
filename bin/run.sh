#!/bin/bash

echo "Running qbit watchdog..."
python /opt/stream_monitor/src/qbitorrent.py &
echo "Running message dispatcher..."
python /opt/stream_monitor/src/app.py



