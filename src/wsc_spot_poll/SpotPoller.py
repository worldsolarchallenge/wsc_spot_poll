import os
import logging
import pprint
import yaml
import statistics
import time

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

        with open(trackers_def, "r") as file:
            self.trackers = yaml.safe_load(file)

        pprint.pprint(self.trackers)

    def poll(self):
        logger.debug("Polling")
        # Poll all the sources

        for tracker in self.trackers:
            time.sleep(5.0)
            logger.debug("Polling " + tracker.name)
            url = "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/%s/message.json" % (
                tracker.feed_id
            )
            logger.debug("Requesting URL " + url)
            r = requests.get(url)
            logger.debug("Requested")

            json = r.json()
            if (
                "response" not in json
                or "feedMessageResponse" not in json["response"]
                or "messages" not in json["response"]["feedMessageResponse"]
            ):
                logger.debug(json)
                return -1

            for message in json["response"]["feedMessageResponse"]["messages"]["message"]:
                try:
                    p = SpotPoint.objects.get(spot_id=message["id"])
                except:
                    if message["messengerId"] != tracker.messenger_id:
                        continue

                    p = SpotPoint(
                        spot_id=message["id"],
                        latitude=message["latitude"],
                        longitude=message["longitude"],
                        sample_time=dateutil.parser.parse(message["dateTime"]),
                        tracker=tracker,
                        message=str(message),
                    )
                    p.save()
                    new_point_callback(p)
                    continue

                #            print str(p) + " was already in the database"
                #            print json

                continue

    def run(self):
        self.running = True
        while self.running:
            self.poll()
            time.sleep(30.0)
