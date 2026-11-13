from django.db.models import Sum


def cart_summary(request):
    """ყველა გვერდისთვის ამატებს კალათაში არსებული ნივთების რაოდენობას."""
    count = 0
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        from .models import CartItem
        count = CartItem.objects.filter(cart__user=user).aggregate(
            total=Sum('quantity')
        )['total'] or 0
    return {'cart_count': count}
