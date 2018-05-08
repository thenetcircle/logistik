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


@app.route('/api/handlers', methods=['GET'])
#@requires_auth
def get_handlers():
    """ Get handlers """
    handlers = environ.env.db.get_all_handlers()
    return api_response(200, [handler.to_json() for handler in handlers])


@app.route('/api/stats/aggregated', methods=['GET'])
#@requires_auth
def get_agg_stats():
    """ Get aggregated statistics """
    agg_stats = environ.env.db.get_all_aggregated_stats()
    return api_response(200, [stat.to_json() for stat in agg_stats])


@app.route('/api/graph', methods=['GET'])
#@requires_auth
def get_graph():
    """ Get aggregated statistics """
    handlers = environ.env.db.get_all_handlers()
    agg_stats = environ.env.db.get_all_aggregated_stats()

    def stats_for(handler: HandlerConf) -> List[AggregatedHandlerStats]:
        matching = list()
        for stat in agg_stats:
            if stat.service_id != handler.service_id:
                logger.info('service_id different: stat={}, handler={}'.format(stat.service_id, handler.service_id))
                continue
            if stat.event != handler.event:
                logger.info('event different: stat={}, handler={}'.format(stat.event, handler.event))
                continue
            if stat.model_type != handler.model_type:
                logger.info('model_type different: stat={}, handler={}'.format(stat.model_type, handler.model_type))
                continue
            if stat.node != handler.node:
                logger.info('node different: stat={}, handler={}'.format(stat.node, handler.node))
                continue
            matching.append(stat)
        return matching

    data = {
        'id': '0',
        'label': 'logistik',
        'children': [{
            'id': 'h-{}'.format(service_id),
            'label': service_id,
            'children': [{
                'id': 'm-{}'.format(handler.identity),
                'label': handler.model_type,
                'children': [{
                    'id': 's-{}-{}-{}'.format(service_id, handler.identity, stat.stat_type),
                    'label': stat.stat_type,
                    'value': stat.count
                } for stat in stats_for(handler)]
            } for handler in handlers if handler.service_id == service_id]
        } for service_id in {handler.service_id for handler in handlers}]
    }

    root = {'id': data['id'], 'value': 1, 'label': data['label']}
    nodes = [root]
    edges = list()

    for handler in data['children']:
        node = {
            'id': handler['id'],
            'value': 1,
            'label': handler['label']
        }
        nodes.append(node)
        edges.append({
            'from': root['id'],
            'to': node['id'],
            'value': 1,
            'title': node['label']
        })

        for model in handler['children']:
            m_node = {
                'id': model['id'],
                'value': 1,
                'label': model['label']
            }
            nodes.append(m_node)
            edges.append({
                'from': node['id'],
                'to': m_node['id'],
                'value': 1,
                'title': m_node['label']
            })

            for stat in model['children']:
                s_node = {
                    'id': stat['id'],
                    'value': 1,
                    'label': stat['label']
                }
                nodes.append(s_node)
                edges.append({
                    'from': m_node['id'],
                    'to': stat['id'],
                    'value': stat['value'],
                    'title': stat['label']
                })

    return api_response(200, {'nodes': nodes, 'edges': edges})


@app.route('/', methods=['GET'])
#@requires_auth
def index():
    floating_menu = str(environ.env.config.get(ConfigKeys.USE_FLOATING_MENU, domain=ConfigKeys.WEB))
    floating_menu = floating_menu.strip().lower() in {'yes', 'y', 'true'}

    handlers = environ.env.db.get_all_handlers()
    stats = environ.env.db.get_all_stats()
    agg_stats = environ.env.db.get_all_aggregated_stats()

    handlers_json = [handler.to_json() for handler in handlers]
    stats_json = [stat.to_json() for stat in stats]
    agg_stats_json = [stat.to_json() for stat in agg_stats]

    return render_template(
        'index_flask.html',
        environment=environment,
        config={
            'ROOT_URL': environ.env.config.get(ConfigKeys.ROOT_URL, domain=ConfigKeys.WEB),
            'FLOATING_MENU': floating_menu
        },
        stats=stats_json,
        agg_stats=agg_stats_json,
        handlers=handlers_json,
        version=tag_name)


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('admin/static/', path)


@app.errorhandler(404)
def page_not_found(_):
    # your processing here
    return index()
