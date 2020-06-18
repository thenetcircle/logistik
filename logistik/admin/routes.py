import json
import logging
import os
import socket
from functools import wraps
from typing import List
from typing import Union
from datetime import datetime as dt

import requests
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import send_from_directory
from git.cmd import Git
from werkzeug.wrappers import Response

from logistik import environ
from logistik.config import ConfigKeys
from logistik.db.reprs.handler import HandlerConf
from logistik.server import app
from logistik.utils.exceptions import HandlerNotFoundException

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

home_dir = os.environ.get('LK_HOME', default=None)
environment = os.environ.get('LK_ENVIRONMENT', default=None)

if home_dir is None:
    home_dir = '.'
tag_name = Git(home_dir).describe()


def is_blank(s: str):
    return s is None or len(s.strip()) == 0


def api_response(code, data: Union[dict, List[dict], str] = None, message: Union[dict, str] = None):
    if data is None:
        data = dict()
    if message is None:
        message = ''

    return jsonify({
        'status_code': code,
        'data': data,
        'message': message
    })


def internal_url_for(url):
    return app.config['ROOT_URL'] + url


def is_authorized():
    enabled = environ.env.config.get(ConfigKeys.OAUTH_ENABLED, domain=ConfigKeys.WEB)
    if str(enabled).lower() in {'false', 'no', '0'}:
        return True

    logging.info(str(request.cookies))
    if 'token' not in request.cookies:
        return False
    return environ.env.web_auth.check(request.cookies.get('token'))


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        state = is_authorized()

        if state is False:
            if request.path.startswith('/api'):
                return api_response(400, message="Invalid authentication.")
            return redirect(internal_url_for('/login'))

        if isinstance(state, Response):
            return state
        return f(*args, **kwargs)
    return decorated


def validate_number(view_func):
    @wraps(view_func)
    def decorator(*args, **kwargs):
        number = args[0]
        if number is None:
            return api_response(400, message='no number specified')

        try:
            int(number)
        except ValueError:
            return api_response(400, message='not a valid number')

        try:
            return view_func(*args, **kwargs)
        except Exception as e:
            logger.error(f'could not run function: {str(e)}')
            raise e
    return decorator


def format_handler(handler: HandlerConf) -> dict:
    info = {
        'identity': handler.identity,
        'event': handler.event,
        'name': handler.name.split('-')[0],
        'node': handler.node,
        'endpoint': handler.endpoint,
        'hostname': handler.hostname,
        'port': handler.port,
        'path': handler.path
    }

    info.update(stats_for_handler(handler.identity))
    return info


@app.route('/api/v1/models')
def list_models():
    handlers = environ.env.db.get_all_activate_handlers()
    return api_response(200, [
        format_handler(handler) for handler in handlers
    ])


@app.route('/api/v1/models/ip/<ip>')
def list_models_for_ip(ip):
    handlers = environ.env.db.get_all_enabled_handlers()
    return api_response(200, [
        format_handler(handler) for handler in handlers
        if handler.event != 'UNMAPPED' and handler.endpoint == ip
    ])


@app.route('/api/v1/hosts')
def list_hosts():
    handlers = environ.env.db.get_all_enabled_handlers()
    hosts = list()
    host_dict = dict()

    for handler in handlers:
        if handler.event == 'UNMAPPED':
            continue

        if handler.endpoint not in host_dict:
            host_dict[handler.endpoint] = list()

        host_dict[handler.endpoint].append(handler)

    for endpoint, host_handlers in host_dict.items():
        hosts.append({
            'ip': endpoint,
            'hostname': host_handlers[0].hostname,
            'models': len(host_handlers)
        })

    return api_response(200, hosts)


def stats_for_handler(handler_id: int):
    try:
        handler = environ.env.db.get_handler_for_identity(handler_id)
        if handler is None:
            raise HandlerNotFoundException(handler_id)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((handler.endpoint, int(handler.port) + 100))

        js = ''
        while True:
            data = s.recv(4096)
            if len(data) < 1:
                break
            js += data.decode('utf8', 'ignore')

        dd = json.loads(js)
        worker = dd['workers'][0]
    except Exception:
        worker = {
            'requests': '',
            'exceptions': '',
            'last_spawn': '',
            'status': 'no stats'
        }
        dd = {'load': ''}

    def format_time(ts):
        if ts == '':
            return ''

        diff = dt.utcnow() - dt.utcfromtimestamp(int(ts))
        total_seconds = diff.total_seconds()
        days = int(total_seconds / (60 * 60 * 24))
        hours = int((total_seconds - days*60*60*24) / (60*60))
        minutes = int((total_seconds - days*60*60*24 - hours*60*60) / 60)

        if days > 0:
            return f'{days}d {hours}h {minutes}m'
        if hours > 0:
            return f'{hours}h {minutes}m'
        return f'{minutes}m'

    return {
        'requests': worker['requests'],
        'exceptions': worker['exceptions'],
        'running_time': format_time(worker['last_spawn']),
        'status': worker['status'],
        'load': dd['load']
    }


@validate_number
@app.route('/api/v1/stats/<handler_id>')
def get_handler_stats(handler_id: str):
    try:
        return api_response(200, stats_for_handler(int(handler_id)))
    except Exception as e:
        return api_response(500, message=f'could not get stats: {str(e)}')


@validate_number
@app.route('/api/v1/query/<handler_id>', methods=['POST'])
def query_model(handler_id):
    handler = environ.env.db.get_handler_for_identity(handler_id)
    url = f'http://{handler.endpoint}:{handler.port}{handler.path}'

    data = json.loads(str(request.data, 'utf-8'))

    response = requests.request(
        method=handler.method, url=url,
        json=data, headers={'Context-Type': 'application/json'}
    )
    logger.info(response)

    return api_response(response.status_code, response.json())


@validate_number
@app.route('/api/v1/logs/<handler_id>', methods=['GET'])
def model_logs(handler_id):
    try:
        handler = environ.env.db.get_handler_for_identity(handler_id)
    except Exception as e:
        logger.error(f'could not get handler: {str(e)}')
        return api_response(400, message='no such handler')

    if handler is None:
        return api_response(400, message='no such handler')

    response = requests.get(url=f'http://{handler.endpoint}:{handler.port}/log')

    lines = list()
    for line in response.json():
        lines.append(line.replace('\n', ''))

    return api_response(response.status_code, '\n'.join(lines))


@app.route('/login')
def login():
    root_url = environ.env.config.get(ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB, default='/')
    callback_url = environ.env.config.get(ConfigKeys.CALLBACK_URL, domain=ConfigKeys.WEB, default=root_url)
    return environ.env.web_auth.auth.authorize(callback=callback_url)


@app.route('/logout')
def logout():
    request.cookies.pop('token', None)
    return redirect(internal_url_for('/login'))


@app.route('/login/callback')
def authorized():
    return environ.env.web_auth.authorized()


@app.route('/api/handlers', methods=['GET'])
@requires_auth
def get_handlers():
    """ Get handlers """
    handlers = environ.env.db.get_all_handlers()
    return api_response(200, [handler.to_json() for handler in handlers])


@app.route('/api/consumers', methods=['GET'])
@requires_auth
def get_consumers():
    consumers = environ.env.handlers_manager.get_handlers()
    return api_response(200, consumers)


@app.route('/api/graph', methods=['GET'])
@requires_auth
def get_graph():
    handlers = environ.env.db.get_all_handlers()
    node_id_enabled = {
        HandlerConf.to_node_id(h.service_id, h.hostname, h.model_type, h.node): h.enabled
        for h in handlers
    }

    service_id_event = {h.service_id: h.event_display_name for h in handlers}
    from uuid import uuid4 as uuid

    data = {
        'id': '0',
        'label': 'logistik',
        'children': [{
            'id': 'h-{}-{}'.format(service_id, str(uuid())),
            'label': service_id,
            'event': service_id_event.get(service_id),
            'children': [{
                'id': 'm-{}'.format(handler.identity),
                'enabled': node_id_enabled.get(HandlerConf.to_node_id(
                    handler.service_id, handler.hostname,
                    handler.model_type, handler.node), False),
                'model_type': handler.model_type,
                'label': '{}-{}-{}'.format(handler.hostname, handler.model_type, handler.node)
            } for handler in handlers if handler.service_id == service_id]
        } for service_id in {h.service_id for h in handlers}]
    }

    root = {'id': data['id'], 'value': 1, 'label': data['label']}
    nodes = [root]
    edges = list()

    for handler in data['children']:
        node = {
            'id': handler['id'],
            'label': handler['label']
        }

        nodes.append(node)
        edges.append({
            'from': root['id'],
            'to': node['id'],
            'label': '{}\n{}'.format(handler['event'], handler['value'])
        })

        for model in handler['children']:
            m_node = {
                'id': model['id'],
                'label': model['label']
            }
            if not model['enabled']:
                m_node['color'] = '#f00'
            elif model['model_type'] == 'canary':
                m_node['color'] = '#D0BB57'

            nodes.append(m_node)
            edges.append({
                'from': node['id'],
                'to': m_node['id'],
                'label': str(model['value'])
            })

    return api_response(200, {'nodes': nodes, 'edges': edges})


@app.route('/', methods=['GET'])
@requires_auth
def index():
    floating_menu = str(environ.env.config.get(ConfigKeys.USE_FLOATING_MENU, domain=ConfigKeys.WEB))
    floating_menu = floating_menu.strip().lower() in {'yes', 'y', 'true'}

    all_handlers = environ.env.db.get_all_handlers(include_retired=True)
    handlers = [handler for handler in all_handlers if not handler.retired]
    consumers = environ.env.handlers_manager.get_handlers()

    handlers_json = [handler.to_json() for handler in handlers]
    all_handlers_json = [handler.to_json() for handler in all_handlers]

    return render_template(
        'index_flask.html',
        environment=environment,
        config={
            'ROOT_URL': environ.env.config.get(ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB),
            'FLOATING_MENU': floating_menu
        },
        consumers=consumers,
        handlers=handlers_json,
        all_handlers=all_handlers_json,
        version=tag_name)


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('admin/static/', path)


@app.errorhandler(404)
def page_not_found(_):
    return index()
