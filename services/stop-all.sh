#!/bin/bash
#
# Stop all Docker-based services.
#
script_dir=${0%/*}

SERVICES="monitoring sos52n gostdashboard geoserver sosemu gost mosquitto phppgadmin postgis grafana-dc grafana chronograf influxdb-dc1 influxdb traefik"
for SERVICE in ${SERVICES}
do
  echo "stopping ${SERVICE}"
  pushd ${script_dir}/${SERVICE}
    ./stop.sh
  popd
done
