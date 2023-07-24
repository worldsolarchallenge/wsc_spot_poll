DOCKER_NAME=wsc_spot_poll
DOCKER_TAG=latest
DOCKER_REPO=dcasnowdon

INFLUX_URL ?= "https://eastus-1.azure.cloud2.influxdata.com"
INFLUX_ORG ?= "BWSC"
INFLUX_BUCKET ?= sample
QUERY_TIME ?= "-2d"1

ENV_VARS=INFLUX_TOKEN INFLUX_BUCKET INFLUX_ORG

export $(ENV_VARS)

.PHONY: build run

all: run

build:
	docker build -t $(DOCKER_NAME):$(DOCKER_TAG) .

run: build
	docker run $(foreach e,$(ENV_VARS),-e $(e)) $(DOCKER_NAME)

publish: build
	docker image tag $(DOCKER_NAME):$(DOCKER_TAG) $(DOCKER_REPO)/$(DOCKER_NAME):$(DOCKER_TAG)
