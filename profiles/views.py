from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
    return render(request, 'profiles/profile.html', {
        'form': form,
        'referral_count': request.user.referrals.count(),
    })


@login_required
def settings_view(request):
    return render(request, 'profiles/settings.html')
