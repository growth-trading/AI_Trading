import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from .models import CustomUser
from .forms import RegisterForm, LoginForm, OTPForm

logger = logging.getLogger(__name__)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        otp = user.generate_otp()
        if _send_otp_email(user, otp):
            messages.success(request, 'Đăng ký thành công! Kiểm tra email để lấy mã xác thực.')
        else:
            messages.warning(request, 'Tài khoản đã tạo nhưng email xác thực gửi thất bại. Vui lòng nhấn "Gửi lại".')
        request.session['pending_verify_user_id'] = user.pk
        return redirect('verify_otp')
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user:
            if not user.is_email_verified:
                request.session['pending_verify_user_id'] = user.pk
                messages.warning(request, 'Vui lòng xác thực email trước khi đăng nhập.')
                return redirect('verify_otp')
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_url = request.GET.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('profile')
        messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('landing')


def verify_otp_view(request):
    user_id = request.session.get('pending_verify_user_id')
    if not user_id:
        return redirect('login')
    try:
        user = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        return redirect('login')

    if user.is_email_verified:
        del request.session['pending_verify_user_id']
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('profile')

    form = OTPForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if user.is_otp_valid(form.cleaned_data['otp']):
            user.is_email_verified = True
            user.otp_code = ''
            user.otp_created_at = None
            user.save(update_fields=['is_email_verified', 'otp_code', 'otp_created_at'])
            del request.session['pending_verify_user_id']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Xác thực email thành công! Chào mừng bạn.')
            return redirect('profile')
        messages.error(request, 'Mã OTP không đúng hoặc đã hết hạn.')
    return render(request, 'accounts/verify_otp.html', {'form': form, 'email': user.email})


def resend_otp_view(request):
    user_id = request.session.get('pending_verify_user_id')
    if not user_id:
        return redirect('login')
    try:
        user = CustomUser.objects.get(pk=user_id)
        otp = user.generate_otp()
        if _send_otp_email(user, otp):
            messages.success(request, 'Đã gửi lại mã OTP mới vào email của bạn.')
        else:
            messages.error(request, 'Gửi email thất bại. Vui lòng thử lại sau.')
    except CustomUser.DoesNotExist:
        pass
    return redirect('verify_otp')


def _send_otp_email(user, otp):
    subject = '[AITrading] Mã xác thực tài khoản của bạn'
    html_message = render_to_string('emails/otp_email.html', {'user': user, 'otp': otp})
    try:
        send_mail(
            subject=subject,
            message=f'Mã OTP của bạn là: {otp}. Có hiệu lực trong 10 phút.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error('Failed to send OTP email to %s: %s', user.email, e)
        return False
