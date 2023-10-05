"""wsc_spot_poll main entry point"""
import argparse
import logging
import os

from . import spot_poller

logging.basicConfig(level=logging.DEBUG)

# Configure basic logging
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="Gather SPOT data into InfluxDB.")
parser.add_argument(
    "--trackers_def",
    dest="trackers_def",
    type=argparse.FileType("r", encoding="utf-8"),
    default=None,
    help="YAML file providing tracker information.",
)
parser.add_argument(
    "--influx_url",
    default=os.environ.get(
        "INFLUX_URL", "us-east-1-1.aws.cloud2.influxdata.com"
    ),
)
parser.add_argument("--influx_org", default=os.environ.get("INFLUX_ORG", "Bridgestone World Solar Challenge"))
parser.add_argument("--influx_token", default=os.environ.get("INFLUX_TOKEN", None))
parser.add_argument("--influx_bucket", default=os.environ.get("INFLUX_BUCKET", None))
parser.add_argument("--spot_token", default=os.environ.get("SPOT_TOKEN", None))

args = parser.parse_args()

# Run the spot poller
poller = spot_poller.SpotPoller(
    influx_url=args.influx_url,
    influx_org=args.influx_org,
    influx_token=args.influx_token,
    influx_bucket=args.influx_bucket,
    spot_token=args.spot_token,
    trackers_def=args.trackers_def,
)
poller.run()
