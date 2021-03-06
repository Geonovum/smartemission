#!/bin/bash
#
# Run the InfluxDB from https://hub.docker.com/_/influxdb/.
#

#LOG_DIR="/var/smartem/log/influxdb"
#DATA_DIR="/var/smartem/data/influxdb"
#BACKUP_DIR="/var/smartem/backup/influxdb"
#NAME="influxdb"
#IMAGE="influxdb:1.4.2"
#
#sudo mkdir -p ${DATA_DIR}
#sudo mkdir -p ${LOG_DIR}
#sudo mkdir -p ${BACKUP_DIR}
#
#SCRIPT_DIR=${0%/*}
#pushd ${SCRIPT_DIR}
#SCRIPT_DIR=$PWD
#popd
#
#VOL_MAP="-v ${DATA_DIR}:/var/lib/influxdb -v ${LOG_DIR}:/var/log/influxdb -v ${SCRIPT_DIR}/config/influxdb.conf:/etc/influxdb/influxdb.conf:ro -v ${BACKUP_DIR}:/backup"
#
## 8083 is admin, 8086 API NB: admin 8083 was removed in InfluxDB 1.3
#PORT_MAP="-p 8086:8086"
#
## Stop and remove possibly old containers
#sudo docker stop ${NAME} > /dev/null 2>&1
#sudo docker rm ${NAME} > /dev/null 2>&1
#
## Finally run, keeping DB-data, config and logs on the host
#sudo docker run --name ${NAME} --network="se_back" ${PORT_MAP} ${VOL_MAP} -d -t ${IMAGE} -config /etc/influxdb/influxdb.conf

# Need HOSTNAME within docker-compose for host-specific path to env file.
mkdir -p /var/smartem/data/influxdb-dc1
mkdir -p /var/smartem/backup/influxdb-dc1

docker-compose rm --force --stop
docker-compose up -d

# generate conf: docker run --rm influxdb influxd config > influxdb.conf
# create db: curl -G http://localhost:8086/query --data-urlencode "q=CREATE DATABASE mydb"