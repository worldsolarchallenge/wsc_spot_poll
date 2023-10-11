DOCKER_NAME=wsc_spot_poll
DOCKER_TAG=latest
DOCKER_REPO=dcasnowdon

INFLUX_URL ?= us-east-1-1.aws.cloud2.influxdata.com
INFLUX_ORG ?= "Bridgestone World Solar Challenge"
INFLUX_BUCKET ?= test
INFLUX_TOKEN ?= $(shell cat wsc_bucket_token.key)

ENV_VARS=INFLUX_TOKEN INFLUX_BUCKET INFLUX_ORG INFLUX_URL

export $(ENV_VARS)

.PHONY: build run

all: run

build:
	docker build -t $(DOCKER_NAME):$(DOCKER_TAG) .

run: build
	docker run \
			$(foreach e,$(ENV_VARS),-e $(e)) \
			-v $$(pwd)/config.yaml:/config.yaml \
			$(DOCKER_NAME)

publish: build
	docker image tag $(DOCKER_NAME):$(DOCKER_TAG) $(DOCKER_REPO)/$(DOCKER_NAME):$(DOCKER_TAG)


build/testenv:
	mkdir build
	python3 -m venv build/testenv
	source build/testenv/bin/activate && pip install -e .

localtest: build/testenv
	source $</bin/activate && \
	    INFLUX_TOKEN=$$(cat wsc_bucket_token.key) \
    	python3 \
        	-m wsc_spot_poll \
        	--config config-new.yaml \
			$(if $(DEBUG),--debug)

lint: build/testenv
	source $</bin/activate && \
		pip install pylint && \
		pylint $$(git ls-files '*.py')


clean:
	rm -rf build