import logging
from typing import List

from flask import jsonify
from flask import request

from logistik import environ
from logistik.server import app

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def api_response(code, data: List[dict] = None, message: str = None):
    if data is None:
        data = list()
    if message is None:
        message = ''

    return jsonify({
        'status_code': code,
        'data': data,
        'message': message
    })


@app.route('/api/v1/handle/<topic_name>', methods=['POST'])
def handle_event(topic_name):
    try:
        data = request.get_data()
    except Exception as e:
        logger.error(f'could not get data from request: {str(e)}')
        return api_response(400, message='could not get data from request')

    try:
        responses = environ.env.handlers_manager.handle_event(topic_name, data)
    except Exception as e:
        logger.error(f'could not get handler: {str(e)}')
        return api_response(500, message=f'failed to handle event: {str(e)}')

    if responses is None:
        return api_response(500, message='could not get responses')

    return api_response(200, data=responses)
