from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _incr_with_ttl(key, window):
    """Atomic increment với TTL — tránh race condition."""
    try:
        return cache.incr(key)
    except ValueError:
        cache.add(key, 0, window)
        return cache.incr(key)


class IPRateLimitMiddleware:
    """
    Chặn brute force và DDoS cơ bản theo IP.
    Chạy trước session/auth nên từ chối sớm, không tốn DB query.
    """

    # (path_prefix, max_req, window_giây)
    _ENDPOINT_LIMITS = [
        ('/accounts/login/',       20, 60),   # 20 req/phút — bao gồm GET page load
        ('/accounts/register/',    10, 60),   # 10 req/phút
        ('/accounts/resend-otp/',   3, 60),   # 3 req/phút
    ]
    _GLOBAL_MAX = 300  # req/phút/IP cho mọi endpoint khác
    _GLOBAL_WIN = 60

    _SKIP_PREFIXES = ('/static/', '/media/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if any(path.startswith(p) for p in self._SKIP_PREFIXES):
            return self.get_response(request)

        ip = _get_client_ip(request)
        if self._is_limited(ip, path):
            is_ajax = (
                request.headers.get('Accept', '').startswith('application/json')
                or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            )
            if is_ajax:
                return JsonResponse({'error': 'Quá nhiều yêu cầu. Vui lòng thử lại sau.'}, status=429)
            return HttpResponse(
                'Too Many Requests — vui lòng thử lại sau ít phút.',
                status=429, content_type='text/plain; charset=utf-8',
            )
        return self.get_response(request)

    def _is_limited(self, ip, path):
        for prefix, max_req, window in self._ENDPOINT_LIMITS:
            if path.startswith(prefix):
                key = f'rl:ep:{prefix}:{ip}'
                return _incr_with_ttl(key, window) > max_req
        return _incr_with_ttl(f'rl:g:{ip}', self._GLOBAL_WIN) > self._GLOBAL_MAX


class EmailVerifiedMiddleware:
    EXEMPT_PREFIXES = ('/accounts/', '/admin/', '/static/', '/media/')
    EXEMPT_EXACT = {'/', '/favicon.ico'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.user.is_email_verified
            and request.path not in self.EXEMPT_EXACT
            and not any(request.path.startswith(p) for p in self.EXEMPT_PREFIXES)
        ):
            # POST và AJAX request trả JSON 403 thay vì redirect để tránh mất dữ liệu form
            is_ajax = (
                request.headers.get('Accept', '').startswith('application/json')
                or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            )
            if request.method == 'POST' or is_ajax:
                return JsonResponse({'error': 'Chưa xác thực email. Vui lòng xác thực tài khoản.'}, status=403)
            request.session['pending_verify_user_id'] = request.user.pk
            messages.warning(request, 'Vui lòng xác thực email trước khi truy cập tính năng này.')
            return redirect('verify_otp')
        return self.get_response(request)
