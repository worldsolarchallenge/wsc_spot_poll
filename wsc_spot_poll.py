import os
import logging
import pprint
import statistics

from influxdb_client import InfluxDBClient

# Configure basic logging
logging.basicConfig()
logger = logging.getLogger('spot_poll')

# Acquire influx authentication details. 
INFLUX_URL = os.environ.get(
    "INFLUX_URL", "https://eastus-1.azure.cloud2.influxdata.com"
)
INFLUX_ORG = os.environ.get("INFLUX_ORG", "BWSC")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", None)

INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "sample")

QUERY_TIME = os.environ.get("QUERY_TIME", "-2d")


if not INFLUX_TOKEN:
    raise ValueError("No InfluxDB token set using INFLUX_TOKEN "
                     "environment variable")




class SpotPoller:
    debug = False
    running = False

    def __init__(self, debug=False):
        logging.debug("Initialising SpotPoller")
        #FIXME: Pass in the influx details. 
        self.influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG,
                        debug=debug)

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

print("Hello!")

#if __name__ == "__main__":
#    poller = SpotPoller(debug=True)
#    poller.run(debug=True)

def main():
    print("Hello World!")

if __name__ == "__main__":
    main()