def broker_services(request):
    from .models import BrokerService
    return {'broker_services': BrokerService.objects.filter(is_active=True)}
