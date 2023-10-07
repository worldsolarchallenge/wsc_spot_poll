"""SpotPoller module monitors a SPOT tracker feed"""
import decimal
import json
import logging
import pprint
import time

import dateutil
import requests
import yaml

from influxdb_client_3 import InfluxDBClient3

logger = logging.getLogger(__name__)


class SpotPoller: # pylint: disable=too-many-instance-attributes
    """Polls a set of SPOT trackers, then publishes to influxdb"""

    def __init__(
        self,
        influx_url=None,
        influx_org=None,
        influx_token=None,
        influx_bucket=None,
        spot_token=None,
        trackers_def=None,
        dry_run=False,
    ):  # pylint: disable=too-many-arguments
        logger.debug("Initialising SpotPoller")
        # InfluxDB Client
        if not influx_token:
            raise ValueError("No InfluxDB token set")

        if not influx_url:
            raise ValueError("No InfluxDB host set")

        if not influx_org:
            raise ValueError("No InfluxDB org set")

        self.influx = InfluxDBClient3(host=influx_url, token=influx_token, org=influx_org, database=influx_bucket)

        self.influx_bucket = influx_bucket

        self.spot_token = spot_token

        self.dry_run = dry_run

        # Dict of recently added messages per feed to avoid repeatedly adding duplicates.
        self.recently_added = {}

        # Load the config from the yaml
        config = yaml.safe_load(trackers_def)

        spot_config = config.get("spot", {})
        self.recently_added_max = spot_config.get("recently_added_max", 1000)
        logger.debug("recently_added_max: %d", self.recently_added_max)

        # From:
        # https://www.findmespot.com/en-us/support/spot-trace/get-help/general/spot-api-support
        # ```Please allow at least 2.5 minutes between calls of the same feed and if you are pulling
        # multiple feeds have your application sleep at least 2 seconds between feed requests.```
        self.update_period = spot_config.get("update_period", 150)
        logger.debug("update_period: %d", self.update_period)

        global_tags = config.get("global_tags", {})
        logger.debug("global_tags: %s", global_tags)

        # Derive a dictionary of feeds from the trackers
        self.feeds = {}
        self.trackers = {}
        for tracker_id, tracker in config["cars"].items():
            logger.debug(tracker_id)

            self.trackers[tracker_id] = tracker
            self.trackers[tracker_id]["tags"].update(global_tags)

            feed = tracker["spot"]["feed_id"]
            if feed not in self.feeds:
                self.feeds[feed] = []
            self.feeds[feed].append(tracker_id)

    #        pprint.pprint(self.trackers)
    #        pprint.pprint(self.feeds)

    def poll(self):
        """Poll SPOT once"""
        logger.debug("Polling")
        # Poll the feeds and add the data to the DB.

        first_feed = True
        for feed in self.feeds:
            if not first_feed:
                logger.debug("Sleeping 2s between feeds")
                time.sleep(2.0)
                first_feed = False

            logger.debug("Polling %s", feed)
            url = f"https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/{feed}/message.json"
            logger.debug("Requesting URL %s", url)
            r = requests.get(url, timeout=30)

            stats = {}
            stats["duplicate_count"] = 0
            stats["new_message_count"] = 0

            if feed not in self.recently_added:
                self.recently_added[feed] = set()

            response = r.json()
            if (
                "response" not in response
                or "feedMessageResponse" not in response["response"]
                or "messages" not in response["response"]["feedMessageResponse"]
            ):
                logger.error(response)
                return

            new_message_list = []

            for message in response["response"]["feedMessageResponse"]["messages"]["message"]:
                # Check to see if we just added this.
                if message["id"] in self.recently_added[feed]:
                    stats["duplicate_count"] += 1
                    # logger.debug("Got a duplicate message: %s", message["id"])
                    continue

                # Add the new message to the recently added and trim to a length limit
                self.recently_added[feed].add(message["id"])

                logging.debug(
                    "Receive SPOT message: id=%s lat=%s long=%s battery=%s sample_time=%s",
                    message["id"],
                    message["latitude"],
                    message["longitude"],
                    message["batteryState"],
                    dateutil.parser.parse(message["dateTime"]),
                )
                logger.debug(
                    "https://www.google.com/maps/search/?api=1&query=%f%%2C%f",
                    float(message["latitude"]),
                    float(message["longitude"]),
                )
                logger.debug("Raw message: %s", str(message))

                # Add this message to our list to send.
                stats["new_message_count"] += 1
                new_message_list.append(message)

            # Send this batch of messages
            self.new_messages(new_message_list, feed=feed)

            # Expire messages from the recently added set.
            recently_added_excess = len(self.recently_added[feed]) - self.recently_added_max
            if recently_added_excess > 0:
                for _ in range(recently_added_excess):
                    logger.debug(
                        "Expiring message from recently_added[%s]: %s", feed, str(next(iter(self.recently_added[feed])))
                    )
                    self.recently_added[feed].remove(next(iter(self.recently_added[feed])))
            logger.debug("Recently added now has %d entries", len(self.recently_added[feed]))

            if not stats["duplicate_count"]:
                logger.warning("All messages in the recent update were new.")

            logger.info(
                "Polled feed %s and added %d messages, ignoring %d duplicates",
                feed,
                stats["new_message_count"],
                stats["duplicate_count"],
            )
            stats.update({"feed": feed})
            logger.info(json.dumps(stats))

    def new_messages(self, messages, feed=None):
        """Function to execute after identifying a new message"""

        points = []

        for message in messages:
            logger.debug("New message: %s feed=%s", message, feed)
            for tracker_id in self.feeds[feed]:
                tracker = self.trackers[tracker_id]

                if tracker["spot"]["messenger_id"] == message["messengerId"]:
                    logger.debug("Adding message for tracker %s", tracker_id)
                    points.append(
                        {
                            "measurement": "telemetry",
                            "tags": tracker["tags"],
                            "fields": {
                                "longitude": decimal.Decimal(message["longitude"]),
                                "latitude": decimal.Decimal(message["latitude"]),
                                "altitude": decimal.Decimal(message["altitude"]),
                                "tracker_battery": message["batteryState"],
                            },
                            "time": int(message["unixTime"] * 1000000000),
                        }
                    )
                    logger.debug("Message timestamp is %d seconds in the past", time.time() - int(message["unixTime"]))

        if not self.dry_run:
            logger.debug("Writing to influx: %s", pprint.pformat(points))
            self.influx.write(database=self.influx_bucket, record=points)
        else:
            logger.info("DRY RUN. Would write: %s", pprint.pformat(points))

    def run(self, dry_run=False):
        """Repeatedly poll for new messages."""
        if dry_run:
            self.dry_run = True

        while True:
            self.poll()
            logger.debug("Sleeping for %d seconds", self.update_period)
            time.sleep(self.update_period)
