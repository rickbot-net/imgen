import asyncio

try:
    import ujson as json
except ImportError:
    import json

import os
import threading
import traceback

import rethinkdb as r
from flask import Flask, render_template, request, g, jsonify, make_response

from dashboard import dash
from utils.db import get_db, get_redis
from utils.ratelimits import ratelimit, endpoint_ratelimit
from utils.exceptions import BadRequest

from sentry_sdk import capture_exception

# Initial require, the above line contains our endpoints.

config = json.load(open('config.json'))
endpoints = None

app = Flask(__name__, template_folder='views', static_folder='views/assets')
app.register_blueprint(dash)

app.config['SECRET_KEY'] = config['client_secret']
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'

if 'sentry_dsn' in config:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(config['sentry_dsn'],
                    integrations=[FlaskIntegration()])


@app.before_first_request
def init_app():
    def run_gc_forever(loop):
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        except (SystemExit, KeyboardInterrupt):
            loop.close()

    gc_loop = asyncio.new_event_loop()
    gc_thread = threading.Thread(target=run_gc_forever, args=(gc_loop,))
    gc_thread.start()
    g.gc_loop = gc_loop

    from utils.endpoint import endpoints as endpnts
    global endpoints
    endpoints = endpnts
    import endpoints as _  # noqa: F401


def require_authorization(func):
    def wrapper(*args, **kwargs):
        if r.table('keys').get(request.headers.get('authorization', '')).coerce_to('bool').default(False).run(get_db()):
            return func(*args, **kwargs)

        return jsonify({'status': 401, 'error': 'You are not authorized to access this endpoint'}), 401

    return wrapper


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'rdb'):
        g.rdb.close()


@app.route('/')
def index():
    return render_template('index.html', active_home="nav-active")


@app.route('/stats', methods=['GET'])
def stats():
    data = {}

    for endpoint in endpoints:
        data[endpoint] = {'hits': get_redis().get(endpoint + ':hits') or 0,
                          'avg_gen_time': endpoints[endpoint].get_avg_gen_time()}

    return render_template('stats.html', data=data, active_stats="nav-active")


@app.route('/endpoints.json', methods=['GET'])
def endpoints():
    return jsonify({"endpoints": [{'name': x, 'parameters': y.params, 'ratelimit': f'{y.rate}/{y.per}s'} for x, y in endpoints.items()]})


@app.route('/documentation')
def docs():
    return render_template('docs.html', url=request.host_url, data=sorted(endpoints.items()), active_docs="nav-active")


@app.route('/api/<endpoint>', methods=['GET', 'POST'])
@require_authorization
@ratelimit
def api(endpoint):
    if endpoint not in endpoints:
        return jsonify({'status': 404, 'error': 'Endpoint {} not found!'.format(endpoint)}), 404
    if request.method == 'GET':
        text = request.args.get('text', '')
        avatars = [x for x in [request.args.get('avatar1', request.args.get('image', None)),
                               request.args.get('avatar2', None)] if x]
        usernames = [x for x in [request.args.get('username1', None), request.args.get('username2', None)] if x]
        kwargs = {}
        for arg in request.args:
            if arg not in ['text', 'username1', 'username2', 'avatar1', 'avatar2']:
                kwargs[arg] = request.args.get(arg)
    else:
        if not request.is_json:
            return jsonify({'status': 400, 'message': 'when submitting a POST request you must provide data in the '
                                                      'JSON format'}), 400
        request_data = request.json
        text = request_data.get('text', '')
        avatars = list(request_data.get('avatars', list(request_data.get('images', []))))
        usernames = list(request_data.get('usernames', []))
        kwargs = {}
        for arg in request_data:
            if arg not in ['text', 'avatars', 'usernames']:
                kwargs[arg] = request_data.get(arg)
    cache = endpoints[endpoint].bucket
    max_usage = endpoints[endpoint].rate
    e_r = endpoint_ratelimit(auth=request.headers.get('Authorization', None), cache=cache, max_usage=max_usage)
    if e_r['X-RateLimit-Remaining'] == -1:
        x = make_response((jsonify({'status': 429, 'error': 'You are being ratelimited'}), 429,
                          {'X-RateLimit-Limit': e_r['X-RateLimit-Limit'],
                           'X-RateLimit-Remaining': 0,
                           'X-RateLimit-Reset': e_r['X-RateLimit-Reset'],
                           'Retry-After': e_r['Retry-After']}))
        return x
    if endpoint == 'profile':
        if request.headers.get('Authorization', None) != config.get('memer_token', None):
            return jsonify({"error": 'This endpoint is limited to RickBot', 'status': 403}), 403
    try:
        result = endpoints[endpoint].run(key=request.headers.get('authorization'),
                                         text=text,
                                         avatars=avatars,
                                         usernames=usernames,
                                         kwargs=kwargs)
    except BadRequest as br:
        traceback.print_exc()
        if 'sentry_dsn' in config:
            capture_exception(br)
        return jsonify({'status': 400, 'error': str(br)}), 400
    except IndexError as e:
        traceback.print_exc()
        if 'sentry_dsn' in config:
            capture_exception(e)
        return jsonify({'status': 400, 'error': str(e) + '. Are you missing a parameter?'}), 400
    except Exception as e:
        traceback.print_exc()
        if 'sentry_dsn' in config:
            capture_exception(e)
        return jsonify({'status': 500, 'error': str(e)}), 500

    result.headers.add('X-RateLimit-Limit', max_usage)
    result.headers.add('X-RateLimit-Remaining', e_r['X-RateLimit-Remaining'])
    result.headers.add('X-RateLimit-Reset', e_r['X-RateLimit-Reset'])
    return result, 200


if __name__ == '__main__':
    app.run(debug=False, use_reloader=False)
