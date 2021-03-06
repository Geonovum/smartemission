.. _kubernetes:

==========
Kubernetes
==========

This chapter describes the installation and maintenance for the Smart Emission Data Platform in a
`Kubernetes (K8s) <https://kubernetes.io/>`_ environment.
Note that installation and maintenance in a Docker environment is described in
the :ref:`installation` chapter. SE was initially (2016-2018) deployed as Containers on a single "bare Docker" machine.
Later with the use of `docker-compose` and Docker Hub but still "bare Docker". In spring 2018 migration within Kadaster-PDOK
to K8s started, deploying in the K8s environment on Azure.

Principles
==========

These are requirements and principles to understand and install an instance of the SE platform.
It is required to have an understanding of `Docker <https://www.docker.com>`_ a
nd `Kubernetes (K8s) <https://kubernetes.io/>`_
as that is the main environment in which the SE Platform is run.

Most Smart Emission services are deployed as follows in K8s:

* deployment.yml - specifies (`Pods` for) a K8s `Deployment`
* service.yml - describes a K8s `Service` (internal network proxy access) for the `Pods` in the `Deployment`
* ingress.yml - rules how to route outside requests to `Service` (only if the `Service` requires outside access)

Only for InfluxDB instances, as it requires local
storage a `StatefulSet` is deployed i.s.o. a regular `Deployment`.

Postgres/PostGIS is not deployed within K8s but accessed as an external
`Azure Database for PostgreSQL server` service from MS Azure.

Install
=======

Install clients.

Ubuntu
------

As follows: ::

	#
	# 1) Install AZ CLI
	#
	# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-apt?view=azure-cli-latest
	$ AZ_REPO=$(lsb_release -cs)
	$ echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_REPO main" | \
	    sudo tee /etc/apt/sources.list.d/azure-cli.list

	# Check
	$ more /etc/apt/sources.list.d/azure-cli.list
	deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ xenial main

	# Get signing key
	$ curl -L https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -

	# Install
	$ apt-get update
	# Problem: https://github.com/Microsoft/WSL/issues/2775
	$ apt-get install python-dev build-essential libffi-dev libssl-dev
	$ apt-get install apt-transport-https azure-cli

	#
	# 2) Install kubectl
	#
	$ az aks install-cli
    $ which kubectl
    /usr/local/bin/kubectl

	#
	# 3) Get cluster creds
	#
	$ az aks get-credentials --resource-group <rsc group name> --name <cluster name>
	# View config
    $ kubectl config view
    
	#
	# 4) Open k8s dashboard in browser
	#
	$ az aks browse --resource-group <rsc group name> --name <cluster name>


Links
=====

Links to the main artefacts related to Kubernetes deployment:

* K8s deployment specs and Readme: https://github.com/smartemission/kubernetes-se (NB not used anymore, repo is in GitLab: https://gitlab.com/smartemission/sensor-cloud-k8s)
* GitHub repositories for all SE Docker Images: https://github.com/smartemission  (all `docker-se-*` repos)
* Docker Images repo: https://hub.docker.com/r/smartemission

Setup
=====

Setting up local environment to interact with K8s cluster on Azure.

Mac OSX
-------

Using Homebrew. Need to install `kubernetes-cli` and `az-cli`: ::

	$ brew install azure-cli
	
    $ brew install kubernetes-cli

Updating
========

For Deployments, CronJobs, StatefulSets, the current sequence of actions to roll out
new updates for code or config changes in Docker Images, is as follows (pre-CI/CD):

* make code changes in related GH repo, e.g `docker-se-stetl <https://github.com/smartemission/docker-se-stetl>`_ for ETL changes
* increase the GH tag number: `git tag` to list current tags, then: `git tag <new version nr>` and `git push --tags`
* add a new build with the tag just added for this component in SmartEmission Organisation in DockerHub, e.g. `smartemission/se-stetl <https://hub.docker.com/r/smartemission/se-stetl/~/settings/automated-builds/>`_
* trigger the build there in DockerHub, wait until build finished and succesful
* increase version number in the Deployment YAML, e.g. the GeoServer  `deployment.yml <https://github.com/smartemission/kubernetes-se/blob/master/smartemission/services/geoserver/deployment.yml>`_
* upgrade current Deployment (or Cronjob StatefulSet) to the Cluster `kubectl -n smartemission replace  -f deployment.yml`
* follow in K8s Dashboard or with `kubectl` for any errors

(TODO: automate this via Jenkins or some CI/CD tooling).

Namespaces
==========

The main two operational K8s `Namespaces` are:

* `smartemission` - the main SE service stack and ETL
* `collectors` - Data Collector services and Dashboards (see global :ref:`architecture` Chapter)

Additional, supporting, `Namespaces` are:

* `monitoring` - Monitoring related
* `cert-manager` - (Let's Encrypt) SSL certificate management
* `ingress-nginx` - Ingress services based on nginx-proxying (external/public access)
* `kube-system` - mainly K8s Dashboard related


Namespace smartemission
=======================

Below are the main K8s artefacts related under the `smartemission` operational `Namespace`.


InfluxDB
--------

InfluxDB holds data for:

* Calibration Learning Process: RIVM reference Data and SE raw data for learning
* Refined Data: calibrated hour-values from refiner ETL process for comparing with ref data

Links
~~~~~

* K8s deployment specs and backup/restore scripts: https://github.com/smartemission/kubernetes-se/tree/master/smartemission/services/influxdb
* GitHub repo/var specs: https://github.com/smartemission/docker-se-influxdb

Creation
~~~~~~~~

Create two volumes via `PersistentVolumeClaim` (pvc.yml) , one for storage, one for backup/restore: ::

	# Run this once to make volumes
	apiVersion: apps/v1beta2
	kind: PersistentVolumeClaim
	metadata:
	  name: influxdb-backup
	spec:
	  accessModes:
	  - ReadWriteOnce
	  storageClassName: default
	  resources:
	    requests:
	      storage: 2Gi

	---

	apiVersion: apps/v1beta2
	kind: PersistentVolumeClaim
	metadata:
	  name: influxdb-storage
	spec:
	  accessModes:
	  - ReadWriteOnce
	  storageClassName: default
	  resources:
	    requests:
	      storage: 5Gi


Use these in `StatefulSet` deployment: ::

	apiVersion: apps/v1beta2
	kind: StatefulSet
	metadata:
	  name: influxdb
	  namespace: smartemission
	spec:
	  selector:
	    matchLabels:
	      app: influxdb
	  serviceName: "influxdb"
	  replicas: 1
	  template:
	    metadata:
	      labels:
	        app: influxdb
	    spec:
	      terminationGracePeriodSeconds: 10
	      containers:
	      - name: influxdb
	        image: influxdb:1.6.1
	        env:
	          - name: INFLUXDB_DB
	            value: smartemission
	          - name: INFLUXDB_ADMIN_USER
	            valueFrom:
	              secretKeyRef:
	                name: influxdb
	                key: username
					.
					.
					.

	          - name: INFLUXDB_DATA_INDEX_VERSION
	            value: tsi1
	          - name: INFLUXDB_HTTP_AUTH_ENABLED
	            value: "true"
	        resources:
	          limits:
	            cpu: "500m"
	            memory: "10.0Gi"
	          requests:
	            cpu: "500m"
	            memory: "1.0Gi"
	        ports:
	        - containerPort: 8086
	        volumeMounts:
	        - mountPath: /var/lib/influxdb
	          name: influxdb-storage
	        - mountPath: /backup
	          name: influxdb-backup
	  volumeClaimTemplates:
	  - metadata:
	      name: influxdb-storage
	    spec:
	      accessModes: [ "ReadWriteOnce" ]
	      storageClassName: default
	      resources:
	        requests:
	          storage: 5Gi
	  - metadata:
	      name: influxdb-backup
	    spec:
	      accessModes: [ "ReadWriteOnce" ]
	      storageClassName: default
	      resources:
	        requests:
	          storage: 2Gi

Backup and Restore
~~~~~~~~~~~~~~~~~~

Backup and restore based on
`InfluxDB documentation <https://docs.influxdata.com/influxdb/v1.6/administration/backup_and_restore>`_

Using the "modern" (v1.5+) InfluxDB backup/restore on live servers with the `portable` backup format.

Before:

* login on maintenance vm
* working kubectl with cluster
* `git clone https://github.com/smartemission/kubernetes-se`
* `cd kubernetes-se/smartemission/services/influxdb`

Example backup/restore ::

	# Test initial
	./test.sh

	# Backup
	./backup.sh influxdb-smartemission_181123.tar.gz

	# Restore
	./restore.sh influxdb-smartemission_181123.tar.gz

	# Test the restore
	./test.sh

CronJobs
--------

K8s `Cronjobs` are applied for all SE ETL.
CronJobs run jobs on a time-based schedule. These automated jobs run like Cron tasks on a Linux or UNIX system.

Links
~~~~~

* GitHub repository: https://github.com/smartemission/docker-se-stetl
* Docker Image: https://hub.docker.com/r/smartemission/se-stetl
* K8s `CronJobs`: https://github.com/smartemission/kubernetes-se/tree/master/smartemission/cronjobs

Implementation
~~~~~~~~~~~~~~

All ETL is based on `the Stetl ETL framework <http://stetl.org>`_.
A single Docker Image based on the official Stetl Docker Image
contains all ETL processes. A start-up parameter determines the specific ETL process to run.
Design of the ETL is described in the :ref:`data` chapter.


