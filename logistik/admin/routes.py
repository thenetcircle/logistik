import logging
import os
from functools import wraps
from typing import List
from typing import Union

from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import send_from_directory
from git.cmd import Git
from werkzeug.wrappers import Response

from logistik import environ
from logistik.config import ConfigKeys
from logistik.server import app
from logistik.db.repr.agg_stats import AggregatedHandlerStats
from logistik.db.repr.handler import HandlerConf

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

home_dir = os.environ.get('LK_HOME', default=None)
environment = os.environ.get('LK_ENVIRONMENT', default=None)

if home_dir is None:
    home_dir = '.'
tag_name = Git(home_dir).describe()


def is_blank(s: str):
    return s is None or len(s.strip()) == 0


def api_response(code, data: Union[dict, List[dict]]=None, message: Union[dict, str]=None):
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


@app.route('/promote/<node_id>')
def promote(node_id: str) -> None:
    environ.env.handlers_manager.stop_handler(node_id)
    handler_conf = environ.env.db.promote_canary(node_id)

    if handler_conf is not None:
        environ.env.handlers_manager.start_handler(handler_conf.node_id())

    return redirect('/')


@app.route('/deregister/<consul_service_id>')
def deregister(consul_service_id: str) -> None:
    environ.env.consul.deregister(consul_service_id)
    return redirect('/')


@app.route('/enable/<node_id>')
def enable(node_id: str) -> None:
    environ.env.db.enable_handler(node_id)
    environ.env.handlers_manager.start_handler(node_id)
    return redirect('/')


@app.route('/disable/<node_id>')
def disable(node_id: str) -> None:
    environ.env.handlers_manager.stop_handler(node_id)
    environ.env.db.disable_handler(node_id)
    return redirect('/')


@app.route('/retire/<node_id>')
def retire(node_id: str) -> None:
    environ.env.handlers_manager.stop_handler(node_id)
    environ.env.db.retire_model(node_id)
    return redirect('/')


@app.route('/delete/<node_id>')
def retire(node_id: str) -> None:
    environ.env.handlers_manager.stop_handler(node_id)
    environ.env.db.delete_handler(node_id)
    return redirect('/')


@app.route('/demote/<node_id>')
def demote(node_id: str) -> None:
    environ.env.handlers_manager.stop_handler(node_id)
    handler_conf = environ.env.db.demote_model(node_id)

    if handler_conf is not None:
        environ.env.handlers_manager.start_handler(handler_conf.node_id())

    return redirect('/')


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


@app.route('/api/stats/aggregated', methods=['GET'])
@requires_auth
def get_agg_stats():
    """ Get aggregated statistics """
    agg_stats = environ.env.db.get_all_aggregated_stats()
    return api_response(200, [stat.to_json() for stat in agg_stats])


@app.route('/api/graph', methods=['GET'])
@requires_auth
def get_graph():
    """ Get aggregated statistics """
    def stats_for(handler: HandlerConf) -> List[AggregatedHandlerStats]:
        matching = list()
        for stat in agg_stats:
            if stat.service_id != handler.service_id:
                continue
            if stat.event != handler.event:
                continue
            if stat.model_type != handler.model_type:
                continue
            if stat.node != handler.node:
                continue
            matching.append(stat)
        return matching

    handlers = environ.env.db.get_all_handlers()
    agg_stats = environ.env.db.get_all_aggregated_stats()
    stats_per_service = dict()
    stats_per_node = dict()

    for stat in agg_stats:
        if stat.service_id not in stats_per_service:
            stats_per_service[stat.service_id] = 0
        stats_per_service[stat.service_id] += stat.count

        node_id = HandlerConf.to_node_id(stat.service_id, stat.hostname, stat.model_type, stat.node)
        if node_id not in stats_per_node:
            stats_per_node[node_id] = 0
        stats_per_node[node_id] += stat.count

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
            'value': stats_per_service.get(service_id, 0),
            'children': [{
                'id': 'm-{}'.format(handler.identity),
                'enabled': node_id_enabled.get(HandlerConf.to_node_id(
                    handler.service_id, handler.hostname,
                    handler.model_type, handler.node), False),
                'model_type': handler.model_type,
                'label': '{}-{}-{}'.format(handler.hostname, handler.model_type, handler.node),
                'value': stats_per_node.get(HandlerConf.to_node_id(
                    handler.service_id, handler.hostname,
                    handler.model_type, handler.node), 0),
                'children': [{
                    'id': 's-{}-{}-{}'.format(service_id, handler.identity, stat.stat_type),
                    'label': stat.stat_type,
                    'value': str(stat.count)
                } for stat in stats_for(handler)]
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

            for stat in model['children']:
                s_node = {
                    'id': stat['id'],
                    'label': stat['label'],
                    'group': stat['label']
                }

                nodes.append(s_node)
                edges.append({
                    'from': m_node['id'],
                    'to': stat['id'],
                    'label': stat['value']
                })

    return api_response(200, {'nodes': nodes, 'edges': edges})


@app.route('/', methods=['GET'])
@requires_auth
def index():
    floating_menu = str(environ.env.config.get(ConfigKeys.USE_FLOATING_MENU, domain=ConfigKeys.WEB))
    floating_menu = floating_menu.strip().lower() in {'yes', 'y', 'true'}

    all_handlers = environ.env.db.get_all_handlers(include_retired=True)
    handlers = [handler for handler in all_handlers if not handler.retired]

    agg_stats = environ.env.db.get_all_aggregated_stats()
    consumers = environ.env.handlers_manager.get_handlers()
    timings = environ.env.timing.get_timing_summary()

    handlers_json = [handler.to_json() for handler in handlers]
    all_handlers_json = [handler.to_json() for handler in all_handlers]
    agg_stats_json = [stat.to_json() for stat in agg_stats]

    for handler in handlers_json:
        if handler['node_id'] in timings['node']:
            handler['average'] = '%.2f' % (timings['node'][handler['node_id']]['average'] or 0)
            handler['stddev'] = '%.2f' % (timings['node'][handler['node_id']]['stddev'] or 0)
            handler['min'] = '%.2f' % (timings['node'][handler['node_id']]['min'] or 0)
            handler['max'] = '%.2f' % (timings['node'][handler['node_id']]['max'] or 0)
        else:
            handler['average'] = '---'
            handler['stddev'] = '---'
            handler['min'] = '---'
            handler['max'] = '---'

    for timing in timings['version']:
        timing['average'] = '%.2f' % (timing['average'] or 0)
        timing['stddev'] = '%.2f' % (timing['stddev'] or 0)
        timing['min'] = '%.2f' % (timing['min'] or 0)
        timing['max'] = '%.2f' % (timing['max'] or 0)

    return render_template(
        'index_flask.html',
        environment=environment,
        config={
            'ROOT_URL': environ.env.config.get(ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB),
            'FLOATING_MENU': floating_menu
        },
        timings=timings,
        consumers=consumers,
        agg_stats=agg_stats_json,
        handlers=handlers_json,
        all_handlers=all_handlers_json,
        version=tag_name)


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('admin/static/', path)


@app.errorhandler(404)
def page_not_found(_):
    # your processing here
    return index()
