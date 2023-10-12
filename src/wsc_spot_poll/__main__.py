"""wsc_spot_poll main entry point"""
import argparse
import logging
import os
import pprint
import yaml

from influxdb_client_3 import InfluxDBClient3
import mergedeep

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
parser.add_argument("--influx_token", default=os.environ.get("INFLUX_TOKEN", None))
parser.add_argument("--debug", action="store_true", default=False)

args = parser.parse_args()

if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug("Sending debug output")

logger.debug("Reading config yaml")
config_defaults = {
    "influx":{
        "measurement":"spot",
        "bucket":"test",
        "org":None,
        "url":None,
        "global_tags":{},
    },
    "spot":{
        "feeds":[],
        "update_period": 150,
        "recently_added_max": 1100
    }
}

# Load the config from the yaml
config = mergedeep.merge(config_defaults, yaml.safe_load(args.config))
logging.debug(pprint.pformat(config))

logging.debug(pprint.pformat(config))

logger.debug("Initialising SpotPoller")
# InfluxDB Client
if not args.influx_token:
    raise ValueError("No InfluxDB token set")

if not config["influx"]["url"]:
    raise ValueError("No InfluxDB host set")

if not config["influx"]["org"]:
    raise ValueError("No InfluxDB org set")

influx = InfluxDBClient3(
    token=args.influx_token, host=config["influx"]["url"], org=config["influx"]["org"], database=config["influx"]["bucket"])

# Run the spot poller
poller = spot_poller.SpotPoller(
    influx=influx,
    config=config,
)
poller.run()
