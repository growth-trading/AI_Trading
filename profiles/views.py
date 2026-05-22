from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import ReferralPayout
from accounts.payout import is_payout_window
from django.conf import settings
from django.contrib.auth import get_user_model
from .forms import ProfileForm


@login_required
def profile_view(request):
    form = ProfileForm(instance=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật hồ sơ thành công.')
            return redirect('profile')
    User = get_user_model()
    f1_count = request.user.referrals.count()
    f2_count = User.objects.filter(referred_by__referred_by=request.user).count()
    payout_history = ReferralPayout.objects.filter(user=request.user)[:6]
    return render(request, 'profiles/profile.html', {
        'form': form,
        'f1_count': f1_count,
        'f2_count': f2_count,
        'is_payout_window': is_payout_window(),
        'payout_history': payout_history,
        'min_payout_coins': getattr(settings, 'REFERRAL_MIN_PAYOUT_COINS', 10),
    })


@login_required
def settings_view(request):
    return render(request, 'profiles/settings.html')
