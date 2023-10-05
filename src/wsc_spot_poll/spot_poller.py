"""SpotPoller module monitors a SPOT tracker feed"""
import decimal
import logging
import time

import dateutil
import requests
import yaml

from influxdb_client_3 import InfluxDBClient3

logger = logging.getLogger(__name__)


class SpotPoller:
    """Polls a set of SPOT trackers, then publishes to influxdb"""

    def __init__(
        self,
        influx_url=None,
        influx_org=None,
        influx_token=None,
        influx_bucket=None,
        spot_token=None,
        trackers_def=None,
    ): # pylint: disable=too-many-arguments
        logger.debug("Initialising SpotPoller")
        # InfluxDB Client
        if not influx_token:
            raise ValueError(
                "No InfluxDB token set using INFLUX_TOKEN environment variable"
            )

        if not influx_url:
            raise ValueError(
                "No InfluxDB host set using INFLUX_HOST environment variable"
            )

        if not influx_org:
            raise ValueError(
                "No InfluxDB org set using INFLUX_ORG environment variable"
            )

        logging.info('Token was "%s"', influx_token)

        self.influx = InfluxDBClient3(
            host=influx_url, token=influx_token, org=influx_org, database=influx_bucket
        )

        self.influx_bucket = influx_bucket

        self.spot_token = spot_token

        self.trackers = yaml.safe_load(trackers_def)

        # Dict of recently added messages to avoid repeatedly adding duplicates.
        self.recently_added = set()
        self.recently_added_max = 1000

        self.feeds = {}
        for tracker in self.trackers:
            logger.debug(self.trackers[tracker])
            feed = self.trackers[tracker]["feed_id"]
            if feed not in self.feeds:
                self.feeds[feed] = []
            self.feeds[feed].append(tracker)

#        pprint.pprint(self.trackers)
#        pprint.pprint(self.feeds)

    def poll(self):
        """Poll SPOT once"""
        logging.debug("Polling")
        # Poll the feeds and add the data to the DB.

        for feed in self.feeds:
            time.sleep(5.0)
            logger.debug("Polling %s", feed)
            url = f"https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/{feed}/message.json"
            logger.debug("Requesting URL %s", url)
            r = requests.get(url, timeout=30)
            logger.debug("Requested")

            response = r.json()
            if (
                "response" not in response
                or "feedMessageResponse" not in response["response"]
                or "messages" not in response["response"]["feedMessageResponse"]
            ):
                logger.error(response)
                return

            for message in response["response"]["feedMessageResponse"]["messages"][
                "message"
            ]:
                # Check to see if we just added this.
                if message["id"] in self.recently_added:
                    logging.debug("Got a duplicate message: %s", message["id"])
                    continue

                self.new_message(message, feed=feed)

                # Add the new message to the recently added and trim to a length limit
                self.recently_added.add(message["id"])

                while len(self.recently_added) > self.recently_added_max:
                    self.recently_added.remove(next(iter(self.recently_added)))

                logging.info(
                    "Receive SPOT message: id=%s lat=%s long=%s sample_time=%s",
                    message["id"],
                    message["latitude"],
                    message["longitude"],
                    dateutil.parser.parse(message["dateTime"]),
                )
                logging.debug(
                    "https://www.google.com/maps/search/?api=1&query=%f%%2C%f",
                    float(message["latitude"]),
                    float(message["longitude"]),
                )
                logging.debug("Raw message: %s", str(message))

    def new_message(self, message, feed=None):
        """Function to execute after identifying a new message"""
        logging.debug("New message: %s feed=%s", message, feed)

        points = []

        for tracker_id in self.feeds[feed]:
            tracker = self.trackers[tracker_id]

            if tracker["messenger_id"] == message["messengerId"]:
                logging.debug("Adding message for tracker %s", tracker_id)
                points.append(
                    {
                        "measurement": "telemetry",
                        "tags": {
                            "event": "BWSC2023",
                            "class": tracker["class"],
                            "team": tracker["team"],
                        },
                        "fields": {
                            "longitude": decimal.Decimal(message["longitude"]),
                            "latitude": decimal.Decimal(message["latitude"]),
                            "altitude": decimal.Decimal(message["altitude"]),
                        },
                        "time": int(message["unixTime"] * 1000000000),
                    }
                )

        logging.debug(points)

        self.influx.write(database=self.influx_bucket, record=points)

    def run(self):
        """Repeatedly poll for new messages."""
        while True:
            self.poll()
            time.sleep(2.5 * 60)
