#!/bin/bash

set -ex

. .env

mkdir -p ${GRAFANA_CONNS}

docker compose up -d