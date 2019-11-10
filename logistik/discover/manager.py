import datetime
from typing import Union

import time
import sys
import logging

from logistik.environ import GNEnvironment
from logistik.config import ConfigKeys, ModelTypes, ServiceTags
from logistik.discover.base import BaseDiscoveryService
from logistik.db.reprs.handler import HandlerConf

logging.getLogger('urllib3').setLevel(logging.WARN)


class DiscoveryService(BaseDiscoveryService):
    SERVICE_ID = 'ServiceID'
    SERVICE_ADDRESS = 'ServiceAddress'
    SERVICE_PORT = 'ServicePort'
    SERVICE_TAGS = 'ServiceTags'
    SERVICE_NAME = 'ServiceName'

    def __init__(self, env: GNEnvironment):
        self.env = env
        self.logger = logging.getLogger(__name__)
        self.tag = env.config.get(ConfigKeys.TAG, domain=ConfigKeys.DISCOVERY, default='logistik')
        self.interval = env.config.get(ConfigKeys.INTERVAL, domain=ConfigKeys.DISCOVERY, default=30)

        if self.interval < 1:
            self.interval = 1
        elif self.interval > 3600:
            self.interval = 3600

    def get_enabled_handlers(self):
        handlers = self.env.db.get_all_handlers()
        enabled_handlers_to_check = set()

        for handler in handlers:
            if not handler.enabled:
                continue
            enabled_handlers_to_check.add(handler.node_id())

        return enabled_handlers_to_check

    def poll_services(self):
        """
        poll services reported by the discovery service as running,
        match against the currently running handlers in logistik;
        disable any running handlers no longer in discovery service,
        and enable any new services with no running handler

        :return: nothing
        """
        enabled_handlers_to_check = self.get_enabled_handlers()
        _, data = self.env.consul.get_services()

        for name, metadata in data.items():
            if self.tag not in metadata:
                # not a logistik service
                continue

            _, services = self.env.consul.get_service(name)

            for service in services:
                consul_service_id = service.get(DiscoveryService.SERVICE_ID)
                service_id = service.get(DiscoveryService.SERVICE_NAME)
                service_tags = service.get(DiscoveryService.SERVICE_TAGS)
                service_tags = self.convert_to_dict(service_id, service_tags)

                # assuming it's a model initially that might already exist,
                # and if it doesn't the type will be set to canary when enabling it
                model_type = ModelTypes.MODEL

                node = service_tags.get(ServiceTags.NODE, '0')
                hostname = service_tags.get(ServiceTags.HOSTNAME, None)

                if hostname is None:
                    self.logger.warning(f'hostname is not specified in tags for "{service_id}", ignoring service')
                    continue

                node_id = HandlerConf.to_node_id(service_id, hostname, model_type, node)
                if node_id in enabled_handlers_to_check:
                    enabled_handlers_to_check.remove(node_id)

                # might be an existing model, in which case the node id might change, so check again
                handler_conf = self.enable_handler(service, name, node, hostname, consul_service_id, service_tags)
                if handler_conf is not None and handler_conf.node_id() in enabled_handlers_to_check:
                    enabled_handlers_to_check.remove(handler_conf.node_id())

        self.disable_handlers_no_longer_in_discovery_service(enabled_handlers_to_check)

    def disable_handlers_no_longer_in_discovery_service(self, enabled_handlers: set):
        """
        when a service stops reporting to the discovery service that it is running, we have to disable the reader in
        logistik, so disable the handler.

        :param enabled_handlers: a set of node IDs
        :return: nothing
        """
        for node_id in enabled_handlers:
            self.logger.info(f'enabled node {node_id} no longer in discovery service, disabling')
            self.disable_handler(node_id)

    def disable_handler(self, node_id: str):
        self.env.db.disable_handler(node_id)
        self.env.handlers_manager.stop_handler(node_id)

    def enable_handler(self, service, name, node, hostname, c_id, tags: dict) -> Union[HandlerConf, None]:
        host = service.get(DiscoveryService.SERVICE_ADDRESS)
        port = service.get(DiscoveryService.SERVICE_PORT)
        s_id = service.get(DiscoveryService.SERVICE_NAME)

        handler_conf = self.create_or_update_handler(host, port, s_id, name, node, hostname, c_id, tags)

        self.env.db.register_handler(handler_conf)
        self.env.handlers_manager.start_handler(handler_conf.node_id())
        self.env.cache.reset_enabled_handlers_for(handler_conf.event)
        return handler_conf

    def create_or_update_handler(self, host, port, service_id, name, node, hostname, c_id, tags: dict):
        """
        if the handler already exists, we'll update it in case the reported metadata
        differs, otherwise we'll create a new disabled canary model handler

        :param host: the service address used to invoke the model (can differ from 'hostname')
        :param port: the port to invoke the model at
        :param service_id: the ID of the service
        :param name: user-friendly name of the service
        :param node: the node number in case multiple nodes running, 0 is the default
        :param hostname: user-friendly name to display as the upstream in the ui
        :param c_id: the consul service id
        :param tags: additional metadata about the model
        :return: nothing
        """
        handler = self.env.db.find_one_handler(service_id, hostname, node)

        if handler is not None:
            return self._update_existing_handler(handler, service_id, node, name, hostname, port, host, c_id, tags)

        return self._create_new_handler(service_id, node, name, hostname, port, host, c_id, tags)

    def _update_existing_handler(
            self, handler: HandlerConf, service_id, node, name, hostname, port, host, c_id, tags: dict
    ) -> HandlerConf:
        """
        update the existing handler with possibly updated metadata about the model

        :param handler: the existing handler conf representation
        :param service_id: the ID of the service
        :param node: the node number in case multiple nodes running, 0 is the default
        :param name: user-friendly name of the service
        :param hostname: user-friendly name to display as the upstream in the ui
        :param port: the port to invoke the model at
        :param host: the service address used to invoke the model (can differ from 'hostname')
        :param c_id: the consul service id
        :param tags: additional metadata about the model
        :return: the updated handler conf representation
        """
        if handler.enabled:
            return self.env.db.update_consul_service_id_and_group_id(handler, c_id, tags)

        self.logger.info('registering updated handler "{}": address "{}", port "{}", id: "{}"'.format(
            name, host, port, service_id
        ))
        return self._create_handler(handler, service_id, node, name, hostname, port, host, c_id, tags)

    def _create_new_handler(self, service_id, node, name, hostname, port, host, c_id, tags: dict) -> HandlerConf:
        """
        create a new handler for the upstream model; it will initially be created as a
        disabled canary model that has to be enabled and promoted in the ui

        if a similar upstream handler exists, certain metadata will be copied from that
        handler to this one, such as event name, http path etc., but the handler will
        still be a disabled canary model

        :param service_id: the ID of the service
        :param node: the node number in case multiple nodes running, 0 is the default
        :param name: user-friendly name of the service
        :param hostname: user-friendly name to display as the upstream in the ui
        :param port: the port to invoke the model at
        :param host: the service address used to invoke the model (can differ from 'hostname')
        :param c_id: the consul service id
        :param tags: additional metadata about the model
        :return: the created handler conf representation
        """
        self.logger.info('registering new handler "{}": address "{}", port "{}", id: "{}"'.format(
            name, host, port, service_id
        ))

        handler = self._create_handler(HandlerConf(), service_id, node, name, hostname, port, host, c_id, tags)
        other_service_handler = self.env.db.find_one_similar_handler(service_id)

        # copy known values form previous handler
        if other_service_handler is not None:
            if 'event' not in tags:
                handler.event = other_service_handler.event
            if 'path' not in tags:
                handler.path = other_service_handler.path
            if 'method' not in tags:
                handler.method = other_service_handler.method

        # new handlers is always a disabled canary model, that needs to be enabled in the ui
        handler.model_type = ModelTypes.CANARY
        handler.enabled = False
        return handler

    def _create_handler(
            self, handler: HandlerConf, service_id, node, name, hostname, port, host, c_id, tags: dict
    ):
        handler.enabled = True
        handler.startup = datetime.datetime.utcnow()
        handler.name = name
        handler.service_id = service_id
        handler.group_id = tags.get(ServiceTags.GROUP_ID, None) or service_id.split('-')[0]
        handler.version = tags.get('version', None) or handler.version
        handler.path = tags.get('path', None) or handler.path
        handler.event = tags.get('event', handler.event) or 'UNMAPPED'
        handler.return_to = tags.get('returnto', None) or handler.return_to
        handler.reader_type = tags.get('readertype', handler.reader_type) or 'kafka'
        handler.reader_endpoint = tags.get('readerendpoint', None) or handler.reader_endpoint
        handler.model_type = ModelTypes.MODEL
        handler.node = node
        handler.consul_service_id = c_id
        handler.hostname = hostname
        handler.endpoint = host
        handler.port = port

        return handler

    def convert_to_dict(self, service_id, service_tags):
        tags = dict()

        for tag in service_tags:
            if '=' not in tag:
                continue
            k, v = tag.split('=', maxsplit=1)
            if k in tags:
                self.logger.warning(
                    f'[{service_id}] key "{k}" already in tags dict with value "{tags[k]}", overwriting with "{v}"')
            tags[k] = v

        return tags

    def run(self):
        while True:
            try:
                self.poll_services()
            except InterruptedError:
                self.logger.info('interrupted, shutting down')
                break
            except Exception as e:
                self.logger.error('could not poll service, sleeping for 3 seconds: {}'.format(str(e)))
                self.logger.exception(e)
                self.env.capture_exception(sys.exc_info())

            time.sleep(self.interval)
