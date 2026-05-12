from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import CustomUser
from .forms import RegisterForm, LoginForm, OTPForm
from deposits.models import DepositTransaction


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        otp = user.generate_otp()
        _send_otp_email(user, otp)
        request.session['pending_verify_user_id'] = user.pk
        messages.success(request, 'Đăng ký thành công! Kiểm tra email để lấy mã xác thực.')
        return redirect('verify_otp')
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
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
        login(request, user)
        return redirect('dashboard')

    form = OTPForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if user.is_otp_valid(form.cleaned_data['otp']):
            user.is_email_verified = True
            user.otp_code = ''
            user.save(update_fields=['is_email_verified', 'otp_code'])
            del request.session['pending_verify_user_id']
            login(request, user)
            messages.success(request, 'Xác thực email thành công! Chào mừng bạn.')
            return redirect('dashboard')
        messages.error(request, 'Mã OTP không đúng hoặc đã hết hạn.')
    return render(request, 'accounts/verify_otp.html', {'form': form, 'email': user.email})


def resend_otp_view(request):
    user_id = request.session.get('pending_verify_user_id')
    if not user_id:
        return redirect('login')
    try:
        user = CustomUser.objects.get(pk=user_id)
        otp = user.generate_otp()
        _send_otp_email(user, otp)
        messages.success(request, 'Đã gửi lại mã OTP mới vào email của bạn.')
    except CustomUser.DoesNotExist:
        pass
    return redirect('verify_otp')


@login_required
def dashboard_view(request):
    recent_txs = DepositTransaction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    context = {
        'recent_txs': recent_txs,
        'coins': request.user.coins,
    }
    return render(request, 'dashboard/index.html', context)


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
    except Exception:
        pass
