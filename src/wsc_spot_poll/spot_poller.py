"""SpotPoller module monitors a SPOT tracker feed"""
import json
import logging
import pprint
import time

import dateutil
import requests
import yaml

logger = logging.getLogger(__name__)


class SpotPoller: # pylint: disable=too-many-instance-attributes
    """Polls a set of SPOT trackers, then publishes to influxdb"""

    def __init__(
        self,
        influx=None,
        config=None,
        dry_run=False,
    ):
        self.dry_run = dry_run
        self.influx = influx

        # Dict of recently added messages per feed to avoid repeatedly adding duplicates.
        self.recently_added = {}

        config_defaults = {
            "measurement":"spot",
            "global_tags":{},
            "spot":{
                "feeds":[],
                "update_period": 150,
                "recently_added_max": 1100
            }
        }
        c = config_defaults.copy()

        # Load the config from the yaml
        c.update(yaml.safe_load(config))
        self.config = c
        logging.debug(pprint.pformat(self.config))

        self.recently_added_max = self.config["spot"]["recently_added_max"]
        logger.debug("recently_added_max: %d", self.recently_added_max)

        # From:
        # https://www.findmespot.com/en-us/support/spot-trace/get-help/general/spot-api-support
        # ```Please allow at least 2.5 minutes between calls of the same feed and if you are pulling
        # multiple feeds have your application sleep at least 2 seconds between feed requests.```
        self.update_period =self.config["spot"]["update_period"]
        logger.debug("update_period: %d", self.update_period)

        global_tags = c["global_tags"]
        logger.debug("global_tags: %s", global_tags)

    def poll(self):
        """Poll SPOT once"""
        logger.debug("Polling")
        # Poll the feeds and add the data to the DB.

        first_feed = True
        for feed in self.config["spot"]["feeds"]:
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
                logger.debug("Raw message: %s", pprint.pformat(message))

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
            logger.debug("New message for feed %s: feed=%s", feed, pprint.pformat(message))
            tags = self.config["global_tags"]
            tags["feed"] = feed
            tags["messengerId"] = message["messengerId"]

            fields = message
            del fields["messengerId"]
            fields["altitude"] = float(fields["altitude"])
            points.append(
                {
                    "measurement": self.config["measurement"],
                    "tags": tags,
                    "fields": fields,
                    "time": int(message["unixTime"] * 1000000000),
                }
            )
            logger.debug("Message timestamp is %d seconds in the past", time.time() - int(message["unixTime"]))

        if not self.dry_run:
            logger.debug("Writing to influx: %s", pprint.pformat(points))
            self.influx.write(record=points)
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
