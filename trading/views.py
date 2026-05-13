import json
from datetime import timedelta
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings
from django.views.decorators.http import require_POST
from django.utils import timezone

from accounts.models import CustomUser
from .models import ChartAnalysisLog
from .services import fetch_chart_image, fetch_indicators, analyze_with_gemini


def landing(request):
    if request.user.is_authenticated:
        return redirect('trading')
    return render(request, 'landing/index.html')


def trading_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user
    plans = {
        'week':  settings.AI_PLAN_WEEK_COST,
        'month': settings.AI_PLAN_MONTH_COST,
        'year':  settings.AI_PLAN_YEAR_COST,
    }
    return render(request, 'trading/index.html', {
        'has_ai_access': user.has_ai_trading_access,
        'ai_expires_at': user.ai_trading_expires_at,
        'ai_plans': plans,
    })


_AI_PLAN_DAYS = {'week': 7, 'month': 30, 'year': 365}


@require_POST
def subscribe_ai_trading_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    plan = body.get('plan')
    if plan not in _AI_PLAN_DAYS:
        return JsonResponse({'error': 'Gói không hợp lệ'}, status=400)

    plan_costs = {
        'week':  settings.AI_PLAN_WEEK_COST,
        'month': settings.AI_PLAN_MONTH_COST,
        'year':  settings.AI_PLAN_YEAR_COST,
    }
    cost = plan_costs[plan]
    days = _AI_PLAN_DAYS[plan]
    now = timezone.now()

    try:
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(pk=request.user.pk)
            if user.coins < cost:
                return JsonResponse({'error': 'Không đủ xu. Vui lòng nạp thêm.'}, status=402)

            user.coins -= cost
            if user.ai_trading_expires_at and user.ai_trading_expires_at > now:
                user.ai_trading_expires_at += timedelta(days=days)
            else:
                user.ai_trading_expires_at = now + timedelta(days=days)
            user.save(update_fields=['coins', 'ai_trading_expires_at'])

        return JsonResponse({
            'success': True,
            'expires_at': user.ai_trading_expires_at.isoformat(),
            'coins_remaining': float(user.coins),
        })
    except Exception as e:
        return JsonResponse({'error': f'Đăng ký thất bại: {str(e)}'}, status=500)


@require_POST
def analyze_chart_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)
    if not request.user.is_email_verified:
        return JsonResponse({'error': 'Chưa xác thực email'}, status=403)
    if not request.user.has_ai_trading_access:
        return JsonResponse({'error': 'Bạn chưa mua gói AI Trading'}, status=403)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Dữ liệu không hợp lệ'}, status=400)

    symbol = body.get('symbol', 'OANDA:XAUUSD').strip()
    interval = body.get('interval', '60').strip()

    try:
        image_bytes = fetch_chart_image(symbol, interval)
        indicators = fetch_indicators(symbol, interval)
        result = analyze_with_gemini(image_bytes, indicators, symbol, interval)

        ChartAnalysisLog.objects.create(
            user=request.user,
            symbol=symbol,
            interval=interval,
            **result,
        )

        return JsonResponse({'success': True, 'data': result})

    except Exception as e:
        return JsonResponse({'error': f'Phân tích thất bại: {str(e)}'}, status=500)
