import logging
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import IntegrityError
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from .models import CustomUser, ReferralPayout
from .forms import RegisterForm, LoginForm, OTPForm
from .middleware import _get_client_ip, _incr_with_ttl
from .payout import is_payout_window, send_usdt_bsc

logger = logging.getLogger(__name__)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('landing')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            messages.error(request, 'Email này đã được sử dụng.')
            return render(request, 'accounts/register.html', {'form': form})
        ref_code = form.cleaned_data.get('referral_code_input', '')
        if ref_code:
            try:
                referrer = CustomUser.objects.get(referral_code=ref_code)
                user.referred_by = referrer
                user.save(update_fields=['referred_by'])
            except CustomUser.DoesNotExist:
                pass
        otp = user.generate_otp()
        if _send_otp_email(user, otp):
            messages.success(request, 'Đăng ký thành công! Kiểm tra email để lấy mã xác thực.')
        else:
            messages.warning(request, 'Tài khoản đã tạo nhưng email xác thực gửi thất bại. Vui lòng nhấn "Gửi lại".')
        request.session['pending_verify_user_id'] = user.pk
        return redirect('verify_otp')
    return render(request, 'accounts/register.html', {'form': form})


_LOGIN_FAIL_MAX = 5    # lần thất bại
_LOGIN_FAIL_WIN = 900  # 15 phút


def login_view(request):
    if request.user.is_authenticated:
        return redirect('landing')
    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        ip = _get_client_ip(request)
        fail_key = f'login:fail:{ip}'
        fail_count = cache.get(fail_key, 0)
        if fail_count >= _LOGIN_FAIL_MAX:
            messages.error(request, 'Quá nhiều lần đăng nhập thất bại. Vui lòng thử lại sau 15 phút.')
            return render(request, 'accounts/login.html', {'form': form})

        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user:
                cache.delete(fail_key)
                if not user.is_email_verified:
                    request.session['pending_verify_user_id'] = user.pk
                    messages.warning(request, 'Vui lòng xác thực email trước khi đăng nhập.')
                    return redirect('verify_otp')
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                next_url = request.POST.get('next') or request.GET.get('next', '')
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                    return redirect(next_url)
                return redirect('landing')
            _incr_with_ttl(fail_key, _LOGIN_FAIL_WIN)
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng.')
    return render(request, 'accounts/login.html', {'form': form})


@require_POST
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
        request.session.pop('pending_verify_user_id', None)
        if not request.user.is_authenticated:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('landing')

    form = OTPForm(request.POST or None)
    if request.method == 'POST':
        # Rate-limit: 5 lần thử / 15 phút / user — chặn brute-force OTP 6 chữ số
        otp_rate_key = f'otp:verify:{user.pk}'
        try:
            otp_attempts = cache.incr(otp_rate_key)
        except ValueError:
            cache.add(otp_rate_key, 0, 900)
            otp_attempts = cache.incr(otp_rate_key)
        if otp_attempts > 5:
            user.otp_code = ''
            user.save(update_fields=['otp_code'])
            messages.error(request, 'Quá nhiều lần thử sai. Vui lòng yêu cầu mã mới.')
        elif form.is_valid():
            if user.is_otp_valid(form.cleaned_data['otp']):
                user.is_email_verified = True
                user.otp_code = ''
                user.otp_created_at = None
                user.save(update_fields=['is_email_verified', 'otp_code', 'otp_created_at'])
                request.session.pop('pending_verify_user_id', None)
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Xác thực email thành công! Chào mừng bạn.')
                return redirect('landing')
            else:
                messages.error(request, 'Mã OTP không đúng hoặc đã hết hạn.')

    # Tính thời gian còn lại của OTP từ server để frontend sync đúng
    seconds_left = 0
    if user.otp_created_at:
        expire_at = user.otp_created_at + timezone.timedelta(minutes=10)
        seconds_left = max(0, int((expire_at - timezone.now()).total_seconds()))

    return render(request, 'accounts/verify_otp.html', {
        'form': form,
        'email': user.email,
        'otp_seconds_left': seconds_left,
    })


def resend_otp_view(request):
    user_id = request.session.get('pending_verify_user_id')
    if not user_id:
        return redirect('login')
    # Rate-limit: 1 request / 60s — chặn spam SMTP
    if not cache.add(f'otp:resend:{user_id}', 1, 60):
        messages.warning(request, 'Vui lòng chờ 1 phút trước khi gửi lại OTP.')
        return redirect('verify_otp')
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


@login_required
@require_POST
def request_payout_view(request):
    import re as _re
    user = request.user
    if not user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)
    if not is_payout_window():
        return JsonResponse({'error': 'Chỉ có thể rút hoa hồng vào 2 ngày cuối tháng.'}, status=400)

    min_coins = getattr(settings, 'REFERRAL_MIN_PAYOUT_COINS', 10)
    if user.referral_coins_earned < min_coins:
        return JsonResponse({'error': f'Số xu tối thiểu để rút là {min_coins} xu.'}, status=400)

    wallet = user.payout_wallet.strip()
    if not wallet:
        return JsonResponse({'error': 'Vui lòng cập nhật địa chỉ ví BSC trước khi rút.'}, status=400)
    if not _re.match(r'^0x[0-9a-fA-F]{40}$', wallet):
        return JsonResponse({'error': 'Địa chỉ ví BSC không hợp lệ.'}, status=400)

    now = timezone.now()
    already = ReferralPayout.objects.filter(
        user=user,
        created_at__year=now.year,
        created_at__month=now.month,
        status__in=[ReferralPayout.STATUS_COMPLETED, ReferralPayout.STATUS_PENDING],
    ).exists()
    if already:
        return JsonResponse({'error': 'Bạn đã rút hoa hồng tháng này rồi.'}, status=400)

    amount_coins = user.referral_coins_earned
    amount_usdt = (amount_coins / settings.USDT_TO_COINS_RATE).quantize(Decimal('0.000001'))

    try:
        with transaction.atomic():
            updated = CustomUser.objects.filter(
                pk=user.pk, referral_coins_earned__gte=min_coins
            ).update(referral_coins_earned=F('referral_coins_earned') - amount_coins)
            if not updated:
                return JsonResponse({'error': 'Không đủ xu hoa hồng.'}, status=400)
            payout = ReferralPayout.objects.create(
                user=user,
                wallet_address=wallet,
                amount_coins=amount_coins,
                amount_usdt=amount_usdt,
                status=ReferralPayout.STATUS_PENDING,
            )
    except Exception:
        logger.exception('Failed to create payout for user %s', user.pk)
        return JsonResponse({'error': 'Lỗi tạo yêu cầu rút tiền.'}, status=500)

    try:
        tx_hash = send_usdt_bsc(wallet, amount_usdt)
        payout.status = ReferralPayout.STATUS_COMPLETED
        payout.tx_hash = tx_hash
        payout.processed_at = timezone.now()
        payout.save(update_fields=['status', 'tx_hash', 'processed_at'])
        return JsonResponse({'success': True, 'tx_hash': tx_hash, 'amount_usdt': float(amount_usdt)})
    except Exception as e:
        logger.exception('USDT transfer failed for payout %s (user %s, %s USDT)', payout.pk, user.pk, amount_usdt)
        # KHÔNG tự động hoàn xu vì TX có thể đã được broadcast lên BSC network.
        # Admin cần kiểm tra blockchain bằng tx hash trước khi xử lý thủ công.
        payout.status = ReferralPayout.STATUS_PENDING
        payout.error_message = (
            f'Transfer error: {e}. '
            'TX có thể đã broadcast — admin cần xác minh blockchain trước khi hoàn xu.'
        )
        payout.save(update_fields=['status', 'error_message'])
        return JsonResponse({
            'error': 'Gửi USDT thất bại. Yêu cầu rút tiền sẽ được admin xem xét trong 24h.'
        }, status=500)


def _send_otp_email(user, otp):
    subject = '[RichAITrading] Mã xác thực tài khoản của bạn'
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
