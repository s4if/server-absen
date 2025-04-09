#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
else
  echo ".env file not found. Exiting."
  exit 1
fi

# Stop and remove existing container if running
docker rm -f $CONTAINER_NAME 2>/dev/null

# Run new PostgreSQL container
docker run --rm -d \
  --name $CONTAINER_NAME \
  -e POSTGRES_USER=$POSTGRES_USER \
  -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
  -e POSTGRES_DB=$POSTGRES_DB \
  -p $POSTGRES_PORT:5432 \
  docker.io/postgres:alpine

echo "Waiting for PostgreSQL to be ready..."
until docker exec $CONTAINER_NAME pg_isready -U $POSTGRES_USER > /dev/null 2>&1; do
  sleep 1
done

echo "PostgreSQL is ready."

rm -rf migrations/*
rm -rf instance/*

flask --app server_absen db init
flask --app server_absen db migrate -m "inisial"
flask --app server_absen db upgrade
flask --app server_absen seed-db


echo "Database migrated and seeded."

flask --app server_absen run --debug