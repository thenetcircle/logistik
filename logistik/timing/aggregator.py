import logging
import time
import eventlet

from logistik.db.repr.agg_timing import AggTiming
from logistik.environ import GNEnvironment
from logistik.timing import IDataAggregatorTask

logger = logging.getLogger(__name__)

TEN_MINUTES = 60 * 10
ONE_MINUTE = 60


class DataAggregatorTask(IDataAggregatorTask):
    def __init__(self, env: GNEnvironment):
        self.env = env
        self.last_run = time.time()

    def start(self):
        self.run_once()
        eventlet.spawn(self.run_loop)

    def run_loop(self):
        while True:
            try:
                # TODO: configurable
                if time.time() - self.last_run > TEN_MINUTES:
                    self.run_once()
                    self.last_run = time.time()
                time.sleep(ONE_MINUTE)
            except InterruptedError:
                logger.info('interrupted, shutting down')
                break

    def run_once(self):
        before = time.time()

        timings_per_version = self.env.db.timing_per_host_and_version()
        if len(timings_per_version) == 0:
            return

        for timing in timings_per_version:
            try:
                entity = AggTiming(
                    timestamp=timing['timestamp'],
                    service_id=timing['service_id'],
                    node_id=timing['node_id'],
                    hostname=timing['hostname'],
                    version=timing['version'],
                    model_type=timing['model_type'],
                    average=timing['average'],
                    stddev=timing['stddev'],
                    min_value=timing['min'],
                    max_value=timing['max'],
                    count=timing['count']
                )
            except KeyError as e:
                logger.error(f'KeyError for {str(e)} in entry, ignoring: {str(timing)}')
                logger.exception(e)
                continue

            try:
                self.env.db.save_aggregated_entity(entity)
            except Exception as e:
                logger.error(f'could not save entity: {str(e)}')
                logger.exception(e)
                continue

            try:
                self.env.db.remove_old_timings(entity)
            except Exception as e:
                logger.error(f'could not remove old timings: {str(e)}')
                logger.exception(e)
                continue

        after = time.time()
        logger.info(f'aggregated and deleted {len(timings_per_version)} timings in {"%.2f" % (after-before)}s')
