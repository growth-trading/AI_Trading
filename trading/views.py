from django.shortcuts import render, redirect


def landing(request):
    return render(request, 'landing/index.html')


def trading_view(request):
    if not request.user.is_authenticated:
        return redirect('register')
    return render(request, 'trading/index.html')
