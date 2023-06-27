import dateutil
import os
import logging
import pprint
import requests
import time
import yaml

from influxdb_client import InfluxDBClient

logger = logging.getLogger(__name__)


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
        trackers_def=None,
    ):
        logger.debug("Initialising SpotPoller")
        # FIXME: Pass in the influx details.
        self.influx = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org, debug=debug)

        self.influx_bucket = influx_bucket
        self.spot_token = spot_token

        self.trackers = yaml.safe_load(trackers_def)

        self.feeds = {}
        for tracker in self.trackers:
            logger.debug(self.trackers[tracker])
            feed = self.trackers[tracker]["feed_id"]
            if feed not in self.feeds:
                self.feeds[feed] = []
            self.feeds[feed].append(tracker)

        pprint.pprint(self.trackers)

        pprint.pprint(self.feeds)

    def poll(self):
        # Poll the feeds and add the data to the DB.

        for feed in self.feeds:
            time.sleep(5.0)
            logger.debug("Polling %s", feed)
            url = f"https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/{feed}/message.json" 
            logger.debug("Requesting URL " + url)
            r = requests.get(url)
            logger.debug("Requested")

            response = r.json()
            if (
                "response" not in response
                or "feedMessageResponse" not in response["response"]
                or "messages" not in response["response"]["feedMessageResponse"]
            ):
                logger.debug(response)
                return -1

            for message in response["response"]["feedMessageResponse"]["messages"]["message"]:
                logging.info(
                    "Receive SPOT message: id=%s lat=%s long=%s sample_time=%s raw='%s'",
                    message["id"],
                    message["longitude"],
                    dateutil.parser.parse(message["dateTime"]),
                    str(message),
                )

    def run(self):
        self.running = True
        while self.running:
            self.poll()
            time.sleep(2.5 * 60)
