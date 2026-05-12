from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from deposits.models import DepositTransaction
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
    all_txs = DepositTransaction.objects.filter(user=request.user)
    return render(request, 'profiles/profile.html', {'form': form, 'all_txs': all_txs})
