import os
import logging
import pprint
import statistics

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
        query_api = self.influx.query_api()

        query = f"""
            from(bucket: "{self.influx_bucket}")
                |> range(start: {self.influx_query_time})
                |> filter(fn: (r) => r._measurement == "telemetry"
                                    and (r._field == "latitude"
                                    or r._field == "longitude"
                                    or r._field == "distance"
                                    or r._field == "solarEnergy"
                                    or r._field == "batteryEnergy"))
                |> last()
                |> keep(columns: ["shortname", "_field", "_value"])
                |> pivot(rowKey: ["shortname"],
                                columnKey: ["_field"],
                                valueColumn: "_value")
                |> map(fn: (r) => ({{r with consumption:
                                (r.solarEnergy +
                                    r.batteryEnergy)/r.distance}}))
                |> group()
                |> keep(columns: ["shortname", "distance",
                        "latitude", "longitude", "consumption"])"""

        stream = query_api.query_stream(query)
        rows = list(stream)
        logging.debug(f"Received: {pprint.pformat(rows)}")

        lats = []
        longs = []

    def run(self):
        self.running = True
        while self.running:
            self.poll()
