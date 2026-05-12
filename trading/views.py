from django.shortcuts import render


def landing(request):
    return render(request, 'landing/index.html')


def trading_view(request):
    return render(request, 'trading/index.html')
