#!/bin/bash
# Wrapper script to run pyunimus at a user-defined interval

: "${RUN_INTERVAL:=3600}"  # default to 1 hour

while true; do
  python3 /app/pyunimus.py
  sleep "$RUN_INTERVAL"
done