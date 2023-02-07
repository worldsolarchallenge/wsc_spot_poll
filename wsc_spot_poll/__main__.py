import logging
import os

from . import SpotPoller

logging.basicConfig(level=logging.DEBUG)

logging.debug("Hello, World!")

# Configure basic logging
logger = logging.getLogger("spot_poll")

# Acquire influx authentication details.
INFLUX_URL = os.environ.get(
    "INFLUX_URL", "https://eastus-1.azure.cloud2.influxdata.com"
)
INFLUX_ORG = os.environ.get("INFLUX_ORG", "BWSC")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", None)

INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "sample")

QUERY_TIME = os.environ.get("QUERY_TIME", "-2d")

spot_token = abcdefg

if not INFLUX_TOKEN:
    raise ValueError("No InfluxDB token set using INFLUX_TOKEN " "environment variable")

# Run the spot poller
poller = SpotPoller.SpotPoller(
    influx_url=INFLUX_URL,
    influx_org=INFLUX_ORG,
    influx_token=INFLUX_TOKEN,
    influx_bucket=INFLUX_BUCKET,
    spot_token=spot_token,
)
poller.run()
