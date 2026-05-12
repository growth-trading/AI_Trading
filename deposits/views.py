import re
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from django.conf import settings
from django.utils import timezone
from .models import DepositTransaction
from .tasks import verify_txhash


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

    tx_hash = request.POST.get('tx_hash', '').strip()
    if not tx_hash or not re.match(r'^0x[0-9a-fA-F]{64}$', tx_hash):
        messages.error(request, 'TxHash không hợp lệ. Định dạng đúng: 0x + 64 ký tự hex.')
        return redirect('deposit')

    if DepositTransaction.objects.filter(tx_hash__iexact=tx_hash).exists():
        messages.error(request, 'Giao dịch này đã được xử lý.')
        return redirect('deposit')

    tx_info = verify_txhash(tx_hash)
    if not tx_info:
        messages.error(request, 'Không tìm thấy giao dịch hoặc giao dịch không hợp lệ. '
                                 'Hãy đảm bảo bạn đã chuyển USDT đến đúng địa chỉ ví.')
        return redirect('deposit')

    tx_memo = tx_info.get('memo', '')
    if tx_memo and tx_memo != request.user.memo_code:
        messages.error(request, 'Giao dịch này không thuộc về tài khoản của bạn. '
                                 'Hãy chắc chắn bạn đã ghi đúng mã memo khi chuyển.')
        return redirect('deposit')

    coins_to_credit = tx_info['amount_usdt'] * settings.USDT_TO_COINS_RATE

    with transaction.atomic():
        dep = DepositTransaction.objects.create(
            user=request.user,
            tx_hash=tx_info['tx_hash'],
            amount_usdt=tx_info['amount_usdt'],
            coins_credited=coins_to_credit,
            status=DepositTransaction.STATUS_COMPLETED,
            memo=request.user.memo_code,
            confirmed_at=timezone.now(),
        )
        request.user.__class__.objects.filter(pk=request.user.pk).update(
            coins=F('coins') + coins_to_credit
        )

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
