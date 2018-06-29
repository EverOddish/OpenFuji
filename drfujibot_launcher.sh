#!/bin/bash

_term() { 
    echo "Caught SIGTERM signal!" 
    kill -TERM "$child" 2>/dev/null
    exit
}

trap _term SIGTERM

while : ; do
    python3 drfujibot.py $1 &
    child=$!
    wait "$child"

    echo "drfujibot.py crashed with exit code $?. Respawning..." >&2
    sleep 1
done
