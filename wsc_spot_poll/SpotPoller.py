import os
import logging
import pprint
import statistics

from influxdb_client import InfluxDBClient


class SpotPoller:
    debug = False
    running = False

    def __init__(self, debug=False):
        logging.debug("Initialising SpotPoller")
        # FIXME: Pass in the influx details.
        self.influx = InfluxDBClient(
            url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, debug=debug
        )

    def poll(self):
        logging.debug("Polling")
        query_api = self.influx.query_api()

        query = f"""
            from(bucket: "{INFLUX_BUCKET}")
                |> range(start: {QUERY_TIME})
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
