#!/bin/bash
GRAFANA_HOST='hass'
GRAFANA_PORT=8086
GRAFANA_USER='grafana'
GRAFANA_PASS='solar'

if [ -z $1 ]; then
	echo "DB table name is needed."
	exit 1
fi

echo "Fixing table $1..."

influx -host $GRAFANA_HOST -port $GRAFANA_PORT -username $GRAFANA_USER -password $GRAFANA_PASS -execute "drop measurement $1_backup" -database solar
sleep 3
influx -host $GRAFANA_HOST -port $GRAFANA_PORT -username $GRAFANA_USER -password $GRAFANA_PASS -execute "SELECT * INTO $1_backup from $1 GROUP BY *" -database solar
sleep 3
influx -host $GRAFANA_HOST -port $GRAFANA_PORT -username $GRAFANA_USER -password $GRAFANA_PASS -execute "SELECT * INTO $1_clean from $1 WHERE BAamps>-1 and BAperc>-1 and BAvolt>-1 and DCamps>-1 and DCkwh>-1 and DCkwh2d>-1 and DCvolt>-1 and DCwatt>-1 and PVamps>-1 and PVkwh>-1 and PVkwh2d>-1 and PVvolt>-1 and PVwatt>-1 GROUP BY *" -database solar
sleep 3
influx -host $GRAFANA_HOST -port $GRAFANA_PORT -username $GRAFANA_USER -password $GRAFANA_PASS -execute "drop measurement $1" -database solar
sleep 3
influx -host $GRAFANA_HOST -port $GRAFANA_PORT -username $GRAFANA_USER -password $GRAFANA_PASS -execute "SELECT * INTO $1 from $1_clean GROUP BY *" -database solar
sleep 3
influx -host $GRAFANA_HOST -port $GRAFANA_PORT -username $GRAFANA_USER -password $GRAFANA_PASS -execute "drop measurement $1_clean" -database solar

echo "Done."
