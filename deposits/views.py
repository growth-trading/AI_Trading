import re
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import F
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from .models import DepositTransaction
from .tasks import verify_txhash

logger = logging.getLogger(__name__)

_VERIFY_MISS = object()  # sentinel phân biệt cache miss với cached None


@login_required
def deposit_view(request):
    if not request.user.is_email_verified:
        messages.warning(request, 'Vui lòng xác thực email trước khi nạp tiền.')
        return redirect('verify_otp')

    qs = DepositTransaction.objects.filter(user=request.user)
    context = {
        'admin_wallet': settings.ADMIN_WALLET_ADDRESS,
        'memo_code': request.user.memo_code,
        'recent_txs': qs.order_by('-created_at')[:10],
        'total_tx_count': qs.count(),
        'usdt_to_coins': settings.USDT_TO_COINS_RATE,
    }
    return render(request, 'deposits/deposit.html', context)


@login_required
def submit_txhash_view(request):
    if request.method != 'POST':
        return redirect('deposit')

    if not request.user.is_email_verified:
        messages.warning(request, 'Vui lòng xác thực email trước khi nạp tiền.')
        return redirect('verify_otp')

    # Normalize lowercase trước mọi thao tác (tránh bypass unique constraint)
    tx_hash = request.POST.get('tx_hash', '').strip().lower()
    if not tx_hash or not re.match(r'^0x[0-9a-f]{64}$', tx_hash):
        messages.error(request, 'TxHash không hợp lệ. Định dạng đúng: 0x + 64 ký tự hex.')
        return redirect('deposit')

    # Rate-limit 5 request/phút/user (atomic incr — tránh race condition)
    rate_key = f'dep:rate:{request.user.pk}'
    try:
        rate_count = cache.incr(rate_key)
    except ValueError:
        cache.add(rate_key, 0, 60)
        rate_count = cache.incr(rate_key)
    if rate_count > 5:
        messages.error(request, 'Bạn đang gửi quá nhiều yêu cầu. Vui lòng chờ 1 phút và thử lại.')
        return redirect('deposit')

    # Kiểm tra sớm trước khi gọi BscScan — tránh lãng phí API quota
    if DepositTransaction.objects.filter(tx_hash=tx_hash).exists():
        messages.error(request, 'Giao dịch này đã được xử lý.')
        return redirect('deposit')

    # Cache kết quả verify 60s (kể cả None) để tránh gọi BscScan lặp cho cùng TxHash
    verify_key = f'dep:verify:{tx_hash}'
    tx_info = cache.get(verify_key, _VERIFY_MISS)
    if tx_info is _VERIFY_MISS:
        tx_info = verify_txhash(tx_hash)
        cache.set(verify_key, tx_info, 60 if tx_info else 30)

    if not tx_info:
        messages.error(request, 'Không tìm thấy giao dịch hoặc giao dịch không hợp lệ. '
                                 'Hãy đảm bảo bạn đã chuyển USDT đến đúng địa chỉ ví.')
        return redirect('deposit')

    # Bắt buộc memo phải khớp — memo rỗng cũng từ chối để chặn claim TxHash người khác
    tx_memo = tx_info.get('memo', '')
    if tx_memo != request.user.memo_code:
        messages.error(request, 'Giao dịch này không thuộc về tài khoản của bạn. '
                                 'Hãy chắc chắn bạn đã ghi đúng mã memo khi chuyển.')
        return redirect('deposit')

    coins_to_credit = tx_info['amount_usdt'] * Decimal(str(settings.USDT_TO_COINS_RATE))

    try:
        with transaction.atomic():
            DepositTransaction.objects.create(
                user=request.user,
                tx_hash=tx_info['tx_hash'],   # đã lowercase từ verify_txhash
                amount_usdt=tx_info['amount_usdt'],
                coins_credited=coins_to_credit,
                status=DepositTransaction.STATUS_COMPLETED,
                memo=tx_memo,                  # lưu memo thực từ blockchain
                confirmed_at=timezone.now(),
            )
            request.user.__class__.objects.filter(pk=request.user.pk).update(
                coins=F('coins') + coins_to_credit
            )
    except IntegrityError:
        messages.error(request, 'Giao dịch này đã được xử lý.')
        return redirect('deposit')

    messages.success(
        request,
        f'Nạp tiền thành công! +{coins_to_credit:.2f} xu đã được cộng vào tài khoản.'
    )
    return redirect('deposit')


@login_required
def check_deposit_status(request, deposit_id):
    dep = get_object_or_404(DepositTransaction, pk=deposit_id, user=request.user)
    return JsonResponse({
        'status': dep.status,
        'coins_credited': str(dep.coins_credited),
        'confirmed_at': dep.confirmed_at.isoformat() if dep.confirmed_at else None,
    })
