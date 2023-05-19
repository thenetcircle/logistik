#!/usr/bin/env python
import datetime
import sys
sys.path.insert(0, '')

import ast
import csv
import os
import random
import re
from string import Template
from typing import Optional

import sqlalchemy
import yaml
from PyInquirer import prompt, Separator
from prompt_toolkit.validation import Validator, ValidationError
from sqlalchemy import create_engine, Engine
from sqlalchemy import text
from tabulate import tabulate

from logistik.config import ConfigKeys
from logistik.environ import ConfigDict


class Environment:
    def __init__(self, config_dict):
        self.config = config_dict
        self.engine: Optional[Engine] = None


class PositiveNumberValidator(Validator):
    def validate(self, document):
        if not len(document.text):
            raise ValidationError(
                message="Empty value specified",
                cursor_position=len(document.text)  # move cursor to end
            )

        try:
            v = int(document.text)
            assert v >= 0
        except AssertionError:
            raise ValidationError(
                message="Number can not be negative",
                cursor_position=len(document.text)  # move cursor to end
            )
        except ValueError:
            raise ValidationError(
                message='Please enter a number',
                cursor_position=len(document.text)  # move cursor to end
            )


class PortValidator(Validator):
    def validate(self, document):
        if not len(document.text):
            raise ValidationError(
                message="Empty value specified",
                cursor_position=len(document.text)  # move cursor to end
            )

        try:
            v = int(document.text)
            assert 0 < v < 65536
        except AssertionError:
            raise ValidationError(
                message="Port not in range [1, 65535]",
                cursor_position=len(document.text)  # move cursor to end
            )
        except ValueError:
            raise ValidationError(
                message='Please enter a number',
                cursor_position=len(document.text)  # move cursor to end
            )


class IpValidator(Validator):
    def validate(self, document):
        if not len(document.text):
            raise ValidationError(
                message="Empty value specified",
                cursor_position=len(document.text)  # move cursor to end
            )

        ip = document.text

        if not re.search(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", ip):
            raise ValidationError(
                message=f"The IP address {ip} is not valid",
                cursor_position=len(document.text)  # move cursor to end
            )

        ip_bytes = ip.split(".")

        for ip_byte in ip_bytes:
            if int(ip_byte) < 0 or int(ip_byte) > 255:
                raise ValidationError(
                    message=f"The IP address {ip} is not valid",
                    cursor_position=len(document.text)  # move cursor to end
                )


class NotEmptyValidator(Validator):
    def validate(self, document):
        if not len(document.text):
            raise ValidationError(
                message="Empty value specified",
                cursor_position=len(document.text)  # move cursor to end
            )


class PathValidator(Validator):
    def validate(self, document):
        if not len(document.text):
            raise ValidationError(
                message="Empty value specified",
                cursor_position=len(document.text)  # move cursor to end
            )

        if ' ' in document.text:
            raise ValidationError(
                message="Path can not contains spaces",
                cursor_position=len(document.text)  # move cursor to end
            )

        if document.text[0] != '/':
            raise ValidationError(
                message="Path must start with a slash '/'",
                cursor_position=len(document.text)  # move cursor to end
            )


NAME_IDX = 1
ID_IDX = 0

LIST_QUERY = """
select 
    id, name, event, return_to, endpoint, 
    port, path, node, group_id 
from 
    handler_conf_entity
where
    retired = false and
    enabled = true;
"""

SELECT_QUERY = """
select 
    id, name, event, return_to, failed_topic, group_id, enabled, retired,
    endpoint, port, path, node, method, retries, timeout
from 
    handler_conf_entity 
where 
    id = :id;
"""

ADD_QUERY = """
insert into handler_conf_entity (
    service_id, name, event, enabled, retired, endpoint, hostname, port,
    path, node, method, retries, timeout, return_to, group_id, failed_topic
)
values (
    :service_id, :name, :event, :enabled, :retired, :endpoint, :hostname, :port,
    :path, :node, :method, :retries, :timeout, :return_to, :group_id, :failed_topic
)
returning id;
"""

EDIT_QUERY = """
update 
    handler_conf_entity
set
    service_id = :service_id, name = :name, event = :event, endpoint = :endpoint, hostname = :hostname, port = :port,
    path = :path, node = :node, return_to = :return_to, group_id = :group_id
where
    id = :id;
"""

handler_keys = [
    "ID",
    "Name",
    "Topic",
    "Return-to",
    "Failed topic",
    "Kafka group ID",
    "Enabled",
    "Retired",
    "IP",
    "Port",
    "API path",
    "Node",
    "Method",
    "Retries",
    "Timeout"
]


initial_options = [
    {
        'type': 'list',
        'name': 'environment',
        'message': 'Environment:',
        'choices': [env.split('.')[0] for env in os.listdir('secrets/')]
    },
    {
        'type': 'list',
        'name': 'action',
        'message': 'Action',
        'choices': [
            'list',
            'add',
            'edit',
            Separator(),
            {
                'name': 'disable',
                'disabled': 'Unavailable at this time'
            },
            {
                'name': 'enable',
                'disabled': 'Unavailable at this time'
            }
        ]
    },
    {
        'type': 'input',
        'name': 'filter',
        'message': 'Filter by handler name (blank to skip):',
        'default': '',
        'when': lambda answers: answers['action'] in {'edit', 'list', 'disable'}
    }
]

choose_options = [{
    'type': 'list',
    'name': 'handler',
    'message': 'Handler:',
    'choices': []
}]

add_options = [
    {
        'type': 'input',
        'name': 'name',
        'message': 'Name:',
        'default': f'test-handler-{random.randint(1, 65000)}',
        'validate': NotEmptyValidator
    },
    {
        'type': 'input',
        'name': 'event',
        'message': 'Topic:',
        'default': 'event-test-request',
        'validate': NotEmptyValidator
    },
    {
        'type': 'input',
        'name': 'return_to',
        'message': 'Return-To:',
        'default': 'event-test-response',
        'validate': NotEmptyValidator
    },
    {
        'type': 'input',
        'name': 'endpoint',
        'message': 'IP:',
        'default': '1.1.1.1',
        'validate': IpValidator,
    },
    {
        'type': 'input',
        'name': 'port',
        'message': 'Port:',
        'default': str(random.randint(1, 65000)),
        'validate': PortValidator,
        'filter': lambda val: int(val)
    },
    {
        'type': 'input',
        'name': 'path',
        'message': 'API Path:',
        'default': '/v1/handle',
        'validate': PathValidator
    },
    {
        'type': 'input',
        'name': 'node',
        'message': 'Node:',
        'default': '0',
        'validate': PositiveNumberValidator,
        'filter': lambda val: int(val)
    },
    {
        'type': 'input',
        'name': 'group_id',
        'message': 'Kafka Group ID:',
        'default': 'some-group',
        'validate': NotEmptyValidator
    }
]


def main():
    print()
    options = prompt(initial_options)
    env = load_env(options['environment'])
    env.engine = create_db(env)
    print()

    if options['action'] == 'list':
        handlers = list_handlers(env, options['filter'])
        print()
        print(tabulate(
            handlers,
            headers=[
                'ID', 'Name', 'Topic', 'Return-To', 'IP', 'Port', 'Path', 'Node', 'Group ID'
            ],
            tablefmt='fancy_grid'
        ))

    elif options['action'] == 'add':
        add_handler(env)

    elif options['action'] == 'edit':
        handlers = list_handlers(env, options['filter'])
        edit_handler(env, handlers)

    else:
        print('not implemented yet')


def edit_handler(env: Environment, handlers: list):
    backup_db(env)

    options = choose_options.copy()
    handler_name_to_handler = dict()

    for handler in handlers:
        key = f"ID: {handler[ID_IDX]} NAME: {handler[NAME_IDX]}"
        options[0]["choices"].append(key)
        handler_name_to_handler[key] = handler

    values = prompt(options)

    # cancelled by user
    if not len(values):
        return

    handler_to_edit = handler_name_to_handler[values["handler"]]
    edit_options = add_options.copy()

    try:
        assert int(handler_to_edit[0]) > 0
    except Exception as e:
        print(f"invalid handler ID '{handler_to_edit[0]}': {str(e)}")
        return

    for i in range(len(edit_options[0])):
        # +1 because index 0 is the id
        edit_options[i]['default'] = str(handler_to_edit[i+1])

    values = prompt(edit_options)

    with env.engine.begin() as connection:
        connection.execute(
            text(EDIT_QUERY),
            {
                "service_id": values.get('name'),
                "name": values.get('name'),
                "event": values["event"],
                "endpoint": values.get('endpoint'),
                "hostname": values.get('endpoint'),
                "port": values.get('port'),
                "path": values.get('path'),
                "node": values.get('node'),
                "return_to": values.get('return_to'),
                "group_id": values.get('group_id'),
                "id": handler_to_edit[0]
            }
        )

    # index 0 is the id
    print_handler(env, handler_to_edit[0])


def add_handler(env: Environment):
    values = prompt(add_options)

    # cancelled by user
    if not len(values):
        return

    topic = values["event"]
    failed_topic = "-".join(topic.split("-")[:-1]) + "-failed"

    with env.engine.begin() as connection:
        result = connection.execute(
            text(ADD_QUERY),
            {
                "service_id": values.get('name'),
                "name": values.get('name'),
                "event": topic,
                "enabled": True,
                "retired": False,
                "endpoint": values.get('endpoint'),
                "hostname": values.get('endpoint'),
                "port": values.get('port'),
                "path": values.get('path'),
                "node": values.get('node'),
                "method": 'POST',
                "retries": 3,
                "timeout": 60,
                "return_to": values.get('return_to'),
                "group_id": values.get('group_id'),
                "failed_topic": failed_topic
            }
        )

        [row_id] = result.fetchone()

    print_handler(env, row_id)


def list_handlers(env: Environment, filter_name: str):
    all_handlers = list()
    try:
        with env.engine.connect() as connection:
            result = connection.execute(text(LIST_QUERY))
            for row in result:
                all_handlers.append(row)
    except Exception as e:
        error("Could not connect to db", e)
        return

    handlers = list()
    for handler in all_handlers:
        if len(filter_name) and filter_name not in handler[NAME_IDX]:
            continue
        handlers.append(handler)

    return handlers


def create_db(env: Environment) -> Engine:
    driver = env.config.get(ConfigKeys.DRIVER, domain=ConfigKeys.DATABASE)

    # 'postgres' is deprecated, removed in newer versions
    if driver == 'postgres+psycopg2':
        driver = 'postgresql+psycopg2'

    user = env.config.get(ConfigKeys.USER, domain=ConfigKeys.DATABASE)
    password = env.config.get(ConfigKeys.PASS, domain=ConfigKeys.DATABASE)
    host = env.config.get(ConfigKeys.HOST, domain=ConfigKeys.DATABASE)
    port = env.config.get(ConfigKeys.PORT, domain=ConfigKeys.DATABASE)
    name = env.config.get(ConfigKeys.NAME, domain=ConfigKeys.DATABASE)

    uri = f"{driver}://{user}:{password}@{host}:{port}/{name}"

    return create_engine(uri, echo=False, connect_args={'connect_timeout': 5})


def load_env(env_name: str) -> Environment:
    with open('config.yaml', 'r') as f:
        config_dict = yaml.safe_load(f)

    secrets_path = f"secrets/{env_name}.yaml"

    # first substitute environment variables, which holds precedence over the yaml config (if it exists)
    template = Template(str(config_dict))
    template = template.safe_substitute(os.environ)

    if os.path.isfile(secrets_path):
        try:
            secrets = yaml.safe_load(open(secrets_path))
        except Exception as e:
            raise RuntimeError(
                "Failed to open secrets configuration {0}: {1}".format(
                    secrets_path, str(e)
                )
            )
        template = Template(template)
        template = template.safe_substitute(secrets)

    env_conf = ast.literal_eval(template)

    return Environment(ConfigDict(env_conf))


def print_handler(env: Environment, row_id: int):
    with env.engine.connect() as connection:
        values = connection.execute(
            text(SELECT_QUERY),
            {
                "id": row_id
            }
        )

    new_handler = list()

    for row in values:
        for key, value in zip(handler_keys, row):
            new_handler.append((key, value))
        break

    print()
    print("New handler added:")
    print()
    print(tabulate(new_handler, tablefmt='fancy_grid'))


def backup_db(env: Environment):
    """
    before any editing is done, backup the conf table locally
    """
    with env.engine.connect() as connection:
        result = connection.execute(text("select * from handler_conf_entity;"))

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    filename = f'logistik-conf-backup-{timestamp}.csv'

    with open(filename, 'w') as f:
        output_file = csv.writer(f)
        output_file.writerow(result.keys())
        for row in result:
            output_file.writerow(row)


def error(s, e):
    print()
    print()
    print(f"Error: {s}: {str(e)}")


if __name__ == "__main__":
    main()
