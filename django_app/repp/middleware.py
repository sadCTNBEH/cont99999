import time
from datetime import datetime
import pytz
from django.utils.deprecation import MiddlewareMixin
from loguru import logger
import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from prometheus_client import Counter, Histogram

from repp.views import refresh_access_token, is_token_valid

logger.add('log.log', format='{time} {level} {message}', level="INFO", rotation='10 MB', compression='zip')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class UserInfoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_time = datetime.now(pytz.UTC)
        ip = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        service_source = request.META.get('HTTP_X_SERVICE_NAME', 'unknown')

        request.request_info = {
            'time': str(request_time),
            'ip': ip,
            'user': str(user),
            'service_source': service_source,
        }

        logger.info(request.request_info)
        response = self.get_response(request)
        return response


class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = None
        refresh_token = None

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        elif hasattr(request, 'session'):
            token = request.session.get('access_token')
            refresh_token = request.session.get('refresh_token')

        if token:
            if is_token_valid(token):
                try:
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'], options={"verify_exp": False})
                    exp_timestamp = payload.get('exp')
                    current_timestamp = int(time.time())

                    if exp_timestamp and exp_timestamp - current_timestamp < 60:
                        new_token = refresh_access_token(refresh_token)
                        if new_token:
                            token = new_token
                            if hasattr(request, 'session'):
                                request.session['access_token'] = new_token
                            request.META['HTTP_AUTHORIZATION'] = f'Bearer {new_token}'

                    jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    user_id = payload.get('user_id')
                    User = get_user_model()
                    user = User.objects.filter(id=user_id).first()
                    if user:
                        request.user = user
                    else:
                        request.user = AnonymousUser()
                except jwt.ExpiredSignatureError:
                    request.user = AnonymousUser()
                except jwt.InvalidTokenError:
                    request.user = AnonymousUser()
            else:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()

        response = self.get_response(request)
        return response


REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP Requests',
    ['method', 'endpoint', 'status_code', 'location']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP Request latency',
    ['method', 'endpoint']
)

class MetricsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        method = request.method
        endpoint = request.path
        status_code = response.status_code
        ip = get_client_ip(request)

        REQUEST_COUNT.labels(method=method, endpoint=endpoint,
                             status_code=status_code, location=None).inc()

        resp_time = time.time() - getattr(request, 'start_time', time.time())
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(resp_time)

        return response