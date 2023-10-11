"""wsc_spot_poll main entry point"""
import argparse
import logging
import os

from influxdb_client_3 import InfluxDBClient3

from . import spot_poller

logging.basicConfig(level=logging.INFO)

# Configure basic logging
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Gather SPOT data into InfluxDB.")
parser.add_argument(
    "--config",
    type=argparse.FileType("r", encoding="utf-8"),
    default=None,
    help="YAML file providing spot config.",
)
parser.add_argument(
    "--influx_url",
    default=os.environ.get("INFLUX_URL", "us-east-1-1.aws.cloud2.influxdata.com"),
)
parser.add_argument("--influx_org", default=os.environ.get("INFLUX_ORG", "Bridgestone World Solar Challenge"))
parser.add_argument("--influx_token", default=os.environ.get("INFLUX_TOKEN", None))
parser.add_argument("--influx_bucket", default=os.environ.get("INFLUX_BUCKET", None))
parser.add_argument("--spot_token", default=os.environ.get("SPOT_TOKEN", None))
parser.add_argument("--debug", action="store_true", default=False)

args = parser.parse_args()

if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug("Sending debug output")

logger.debug("Initialising SpotPoller")
# InfluxDB Client
if not args.influx_token:
    raise ValueError("No InfluxDB token set")

if not args.influx_url:
    raise ValueError("No InfluxDB host set")

if not args.influx_org:
    raise ValueError("No InfluxDB org set")

influx = InfluxDBClient3(
    host=args.influx_url, token=args.influx_token, org=args.influx_org, database=args.influx_bucket
)

# Run the spot poller
poller = spot_poller.SpotPoller(
    influx=influx,
    config=args.config,
)
poller.run()
