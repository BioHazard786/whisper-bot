#!/bin/bash
# Start fresh
docker compose down
git pull
docker compose up -d --build --remove-orphans
docker image prune -f