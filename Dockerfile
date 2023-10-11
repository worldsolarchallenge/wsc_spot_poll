FROM almalinux:9 as build
RUN yum install -y python3 python3-pip git && \
    python3 -m pip install --no-cache-dir --upgrade build

COPY . /build
WORKDIR /build

RUN python3 -m build


FROM python:3.11.6-slim as run

#ENV INFLUX_TOKEN
#ENV INFLUX_ORG
#ENV INFLUX_URL
#ENV INFLUX_BUCKET

WORKDIR /

RUN pip3 install --no-cache-dir --upgrade pip

COPY --from=build /build/dist /app

RUN pip3 install --no-cache-dir --upgrade /app/*.whl && rm -r /app


CMD ["python","-m", "wsc_spot_poll", "--config", "/config.yaml", "--debug"]