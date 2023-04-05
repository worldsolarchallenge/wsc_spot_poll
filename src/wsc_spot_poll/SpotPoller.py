import os
import logging
import pprint
import statistics
import time

from influxdb_client import InfluxDBClient


class SpotPoller:
    debug = False
    running = False

    influx_query_time = "-2d"

    def __init__(
        self,
        debug=False,
        influx_url=None,
        influx_org=None,
        influx_token=None,
        influx_bucket=None,
        spot_token=None,
    ):
        logging.debug("Initialising SpotPoller")
        # FIXME: Pass in the influx details.
        self.influx = InfluxDBClient(
            url=influx_url, token=influx_token, org=influx_org, debug=debug
        )

        self.influx_bucket = influx_bucket
        self.spot_token = spot_token

    def poll(self):
        logging.debug("Polling")

    def run(self):
        self.running = True
        while self.running:
            self.poll()
            time.sleep(30.0)