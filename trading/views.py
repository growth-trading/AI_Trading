from django.shortcuts import render, redirect


def landing(request):
    if request.user.is_authenticated:
        return redirect('trading')
    return render(request, 'landing/index.html')


def trading_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'trading/index.html')
