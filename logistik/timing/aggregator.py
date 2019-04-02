import logging
import time
import eventlet
import sys

from logistik.db.models.agg_stats import AggregatedHandlerStatsEntity
from logistik.db.repr.agg_stats import AggregatedHandlerStats
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
        try:
            self.agg_timing_entity()
        except InterruptedError as e:
            raise e
        except Exception as e:
            logger.error(f'exception caught when aggregating TimingEntity: {str(e)}')
            logger.exception(e)
            self.env.capture_exception(sys.exc_info())

        try:
            self.agg_handler_stats_entity()
        except InterruptedError as e:
            raise e
        except Exception as e:
            logger.error(f'exception caught when aggregating HandlerStatsEntity: {str(e)}')
            logger.exception(e)
            self.env.capture_exception(sys.exc_info())

    def agg_handler_stats_entity(self):
        before = time.time()

        stats_per_service = self.env.db.handler_stats_per_service()
        if len(stats_per_service) == 0:
            return

        for stats in stats_per_service:
            try:
                entity = AggregatedHandlerStats(
                    service_id=stats['service_id'],
                    hostname=stats['hostname'],
                    model_type=stats['model_type'],
                    count=stats['count'],
                    stat_type=stats['stat_type'],
                    node=stats['node']
                )
            except KeyError as e:
                logger.error(f'KeyError for {str(e)} in entry, ignoring: {str(stats)}')
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                continue

            try:
                self.env.db.save_aggregated_stats_entity(entity)
            except Exception as e:
                logger.error(f'could not save entity: {str(e)}')
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                continue

            try:
                self.env.db.remove_old_handler_stats(entity)
            except Exception as e:
                logger.error(f'could not remove old handler stats: {str(e)}')
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                continue

        after = time.time()
        logger.info(f'aggregated and deleted {len(stats_per_service)} handler stats in {"%.2f" % (after-before)}s')

    def agg_timing_entity(self):
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
                self.env.db.save_aggregated_timing_entity(entity)
            except Exception as e:
                logger.error(f'could not save entity: {str(e)}')
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                continue

            try:
                self.env.db.remove_old_timings(entity)
            except Exception as e:
                logger.error(f'could not remove old timings: {str(e)}')
                logger.exception(e)
                self.env.capture_exception(sys.exc_info())
                continue

        after = time.time()
        logger.info(f'aggregated and deleted {len(timings_per_version)} timings in {"%.2f" % (after-before)}s')
