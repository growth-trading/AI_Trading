from django.shortcuts import redirect


class EmailVerifiedMiddleware:
    EXEMPT_PREFIXES = ('/accounts/', '/admin/', '/static/', '/media/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.user.is_email_verified
            and not any(request.path.startswith(p) for p in self.EXEMPT_PREFIXES)
        ):
            request.session['pending_verify_user_id'] = request.user.pk
            return redirect('verify_otp')
        return self.get_response(request)
