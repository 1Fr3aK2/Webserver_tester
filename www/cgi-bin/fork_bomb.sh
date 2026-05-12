#!/bin/bash
for i in $(seq 1 20); do
    sleep 5 &
done
echo "Content-Type: text/plain"
echo ""
echo "spawned"
