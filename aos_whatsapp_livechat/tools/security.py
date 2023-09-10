from odoo import http, api, SUPERUSER_ID
from odoo.http import request
from werkzeug.exceptions import Unauthorized, BadRequest
import functools
import json

from datetime import date

import logging
_logger = logging.getLogger(__name__)

def protected():
    def wrapper(func):
        @functools.wraps(func)
        def verify(*args, **kwargs):
            pub_env = api.Environment(http.request.cr, SUPERUSER_ID, {})
            data = json.loads(http.request.httprequest.data.decode("ASCII"))
            print ('====protected====',data)
            if not data.get('client_id') or not data.get('secret_key'):
                raise Unauthorized()
            user = pub_env['res.users'].sudo().search(
                [('rest_secret', '=', data.get('secret_key')), ('rest_id', '=', data.get('client_id'))], limit=1)
            print ('==user==',user,data.get('secret_key'),data.get('client_id'))
            env = api.Environment(http.request.cr, user.id, {})
            if not user:
                #raise Unauthorized()
                _logger.warning('Unauthorized user on receipt account for %s' % data.get('client_id'))
            http.request._env = env
            return func(*args, **kwargs)
        return verify
    return wrapper
