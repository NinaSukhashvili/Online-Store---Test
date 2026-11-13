
from decimal import Decimal
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Exists, Min, OuterRef, Prefetch, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CheckoutForm, ProfileForm, RegisterForm
from .models import (
    Book,
    BookOffer,
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
)


BOOKS_PER_PAGE = 12

# მხოლოდ სასწავლო სიმულაციაა და რეალურ გადახდას არ ასრულებს.
DEMO_CARD_NUMBER = '4242424242424242'


SORT_OPTIONS = {
    'new': ('ახალი დამატებული', ('-created_at', 'title')),
    'price_asc': ('ფასი: ზრდადობით', ('min_price', 'title')),
    'price_desc': ('ფასი: კლებადობით', ('-min_price', 'title')),
    'title': ('სათაური: ა-ჰ', ('title',)),
}


def _books_with_offers():
    """წიგნები, რომლებსაც ამჟამად ნაყიდი შეთავაზება აქვთ."""
    purchasable = BookOffer.objects.purchasable()

    return (
        Book.objects
        .filter(Exists(purchasable.filter(book=OuterRef('pk'))))
        .annotate(
            min_price=Min(
                'offers__price',
                filter=Q(offers__is_available=True) & (
                    Q(offers__format='digital', offers__ebook_file__gt='') |
                    Q(offers__format='physical', offers__stock__gt=0)
                ),
            )
        )
        .select_related('publisher')
        .prefetch_related(
            'authors',
            'categories',
            Prefetch(
                'offers',
                queryset=purchasable.select_related('seller'),
                to_attr='purchasable_offers',
            ),
        )
    )


def _parse_price(value):
    try:
        price = Decimal(value)
    except Exception:
        return None

    return price if price >= 0 else None


# მთავარი გვერდი
def home(request):
    latest_books = _books_with_offers().order_by('-created_at')[:8]
    categories = Category.objects.filter(
        books__isnull=False
    ).distinct()[:12]

    return render(request, 'books/home.html', {
        'books': latest_books,
        'categories': categories,
    })


# წიგნების კატალოგი
def book_list(request):
    books = _books_with_offers()

    search_query = request.GET.get('q', '').strip()

    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(authors__name__icontains=search_query)
        ).distinct()

    category_id = request.GET.get('category', '').strip()
    selected_category = None

    if category_id.isdigit():
        selected_category = Category.objects.filter(
            pk=category_id
        ).first()

        if selected_category:
            books = books.filter(categories=selected_category)

    selected_format = request.GET.get('format', '').strip()

    if selected_format in BookOffer.Format.values:
        books = books.filter(
            Exists(
                BookOffer.objects.purchasable().filter(
                    book=OuterRef('pk'),
                    format=selected_format,
                )
            )
        )
    else:
        selected_format = ''

    min_price_raw = request.GET.get('min_price', '').strip()
    max_price_raw = request.GET.get('max_price', '').strip()

    min_price = _parse_price(min_price_raw) if min_price_raw else None
    max_price = _parse_price(max_price_raw) if max_price_raw else None

    if min_price is not None:
        books = books.filter(min_price__gte=min_price)

    if max_price is not None:
        books = books.filter(min_price__lte=max_price)

    sort = request.GET.get('sort', 'new')

    if sort not in SORT_OPTIONS:
        sort = 'new'

    books = books.order_by(*SORT_OPTIONS[sort][1])

    page_obj = Paginator(
        books,
        BOOKS_PER_PAGE
    ).get_page(request.GET.get('page'))

    return render(request, 'books/book_list.html', {
        'page_obj': page_obj,
        'books': page_obj.object_list,
        'search_query': search_query,
        'categories': Category.objects.filter(
            books__isnull=False
        ).distinct(),
        'selected_category': selected_category,
        'selected_format': selected_format,
        'formats': BookOffer.Format.choices,
        'min_price': min_price_raw if min_price is not None else '',
        'max_price': max_price_raw if max_price is not None else '',
        'sort': sort,
        'sort_options': [
            (key, label)
            for key, (label, _) in SORT_OPTIONS.items()
        ],
    })


# კონკრეტული წიგნის გვერდი
def book_detail(request, book_id):
    book = get_object_or_404(
        Book.objects.select_related('publisher').prefetch_related(
            'authors',
            'categories',
        ),
        id=book_id,
    )

    offers = list(
        book.offers.filter(is_available=True)
        .select_related('seller')
        .order_by('price')
    )

    purchasable = [
        offer for offer in offers
        if offer.is_purchasable
    ]

    cheapest_id = purchasable[0].id if purchasable else None

    return render(request, 'books/book_detail.html', {
        'book': book,
        'offers': offers,
        'cheapest_id': cheapest_id,
    })


# რეგისტრაცია
def register(request):
    if request.user.is_authenticated:
        return redirect('books:home')

    form = RegisterForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)

        messages.success(
            request,
            'რეგისტრაცია წარმატებით დასრულდა. კეთილი იყოს თქვენი მობრძანება!'
        )

        return redirect('books:home')

    return render(request, 'registration/register.html', {
        'form': form,
    })


# კალათა
def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart_view(request):
    cart = _get_cart(request.user)

    items = list(
        cart.items.select_related(
            'offer__book',
            'offer__seller',
        ).order_by('id')
    )

    total = sum(
        (item.total_price for item in items),
        Decimal('0.00'),
    )

    return render(request, 'books/cart.html', {
        'items': items,
        'total': total,
    })


@login_required
@require_POST
def cart_add(request, offer_id):
    offer = get_object_or_404(
        BookOffer.objects.select_related('book'),
        pk=offer_id,
    )

    if not offer.is_purchasable:
        messages.error(
            request,
            'ეს შეთავაზება ამჟამად მიუწვდომელია.'
        )
        return redirect('books:book_detail', book_id=offer.book_id)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1

    quantity = max(quantity, 1)

    cart = _get_cart(request.user)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        offer=offer,
        defaults={'quantity': 0},
    )

    new_quantity = min(
        item.quantity + quantity,
        offer.max_quantity,
    )

    if new_quantity == item.quantity and not created:
        messages.info(
            request,
            'მაქსიმალური რაოდენობა უკვე კალათაშია.'
        )
    else:
        item.quantity = new_quantity
        item.save()

        messages.success(
            request,
            f'„{offer.book.title}“ დაემატა კალათაში.'
        )

    next_url = request.POST.get('next')

    if request.POST.get('go_to_cart') or not next_url:
        return redirect('books:cart')

    return redirect('books:book_detail', book_id=offer.book_id)


@login_required
@require_POST
def cart_update(request, item_id):
    item = get_object_or_404(
        CartItem.objects.select_related('offer'),
        pk=item_id,
        cart__user=request.user,
    )

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = item.quantity

    if quantity < 1:
        item.delete()
        messages.info(request, 'ნივთი კალათიდან ამოიშალა.')
    else:
        capped = min(
            quantity,
            max(item.offer.max_quantity, 1),
        )

        if capped != quantity:
            messages.warning(
                request,
                f'ხელმისაწვდომია მხოლოდ {capped} ეგზემპლარი.'
            )

        item.quantity = capped
        item.save()

    return redirect('books:cart')


@login_required
@require_POST
def cart_remove(request, item_id):
    item = get_object_or_404(
        CartItem,
        pk=item_id,
        cart__user=request.user,
    )

    item.delete()

    messages.info(request, 'ნივთი კალათიდან ამოიშალა.')

    return redirect('books:cart')


# შეკვეთის გაფორმება
@login_required
def checkout(request):
    cart = _get_cart(request.user)

    items = list(
        cart.items.select_related(
            'offer__book',
            'offer__seller',
        ).order_by('id')
    )

    return _process_checkout(request, cart, items)


# კალათის ერთი ნივთის ცალკე შეძენა
@login_required
def checkout_item(request, item_id):
    cart = _get_cart(request.user)

    item = get_object_or_404(
        cart.items.select_related(
            'offer__book',
            'offer__seller',
        ),
        pk=item_id,
    )

    return _process_checkout(request, cart, [item])



def _process_checkout(request, cart, items):
    if not items:
        messages.info(request, 'კალათა ცარიელია.')
        return redirect('books:book_list')

    needs_address = any(
        item.offer.is_physical
        for item in items
    )

    total = sum(
        (item.total_price for item in items),
        Decimal('0.00'),
    )

    initial = {
        'full_name': request.user.get_full_name()
    }

    form = CheckoutForm(
        request.POST or None,
        initial=initial,
        needs_address=needs_address,
    )

    card_error = ''

    if request.method == 'POST' and form.is_valid():

        # სატესტო რეჟიმი:
        # მიიღება ნებისმიერი 16-ნიშნა ბარათის ნომერი.
        # რეალური საბანკო გადახდა არ სრულდება.
        card_number = ''.join(
            character
            for character in request.POST.get('card_number', '')
            if character.isdigit()
        )

        if len(card_number) != 16:
            card_error = 'ბარათის ნომერი უნდა შეიცავდეს ზუსტად 16 ციფრს.'
        else:
            try:
                with transaction.atomic():
                    order = _create_order(
                        request.user,
                        cart,
                        form.cleaned_data,
                        selected_items=items,
                    )

            except ValueError as error:
                messages.error(request, str(error))
                return redirect('books:cart')

            messages.success(
                request,
                'სატესტო გადახდა წარმატებით დასრულდა! '
                'შეკვეთა დადასტურებულია.'
            )

            return redirect(
                'books:order_detail',
                order_id=order.id,
            )

    return render(request, 'books/checkout.html', {
        'form': form,
        'items': items,
        'total': total,
        'needs_address': needs_address,
        'card_error': card_error,
    })



def _create_order(user, cart, data, selected_items=None):
    """ქმნის შეკვეთას და ამოწმებს წიგნების ხელმისაწვდომობას."""

    if selected_items is None:
        cart_items = list(
            cart.items.select_related('offer__book')
        )
    else:
        selected_ids = [
            item.pk for item in selected_items
        ]

        cart_items = list(
            cart.items.filter(
                pk__in=selected_ids
            ).select_related('offer__book')
        )

    if not cart_items:
        raise ValueError('კალათა ცარიელია.')

    offers = {
        offer.pk: offer
        for offer in BookOffer.objects.select_for_update().filter(
            pk__in=[item.offer_id for item in cart_items]
        )
    }

    # შეკვეთა ფიქსირდება მხოლოდ სატესტო ბარათის შემოწმების შემდეგ.
    order = Order.objects.create(
        user=user,
        full_name=data['full_name'],
        phone=data['phone'],
        shipping_address=data.get('shipping_address', ''),
        payment_method=Order.PaymentMethod.CARD,
        payment_status=Order.PaymentStatus.PAID,
        status=Order.Status.CONFIRMED,
    )

    total = Decimal('0.00')

    for item in cart_items:
        offer = offers.get(item.offer_id)
        title = item.offer.book.title

        if offer is None or not offer.is_purchasable:
            raise ValueError(
                f'„{title}“ ამჟამად მიუწვდომელია.'
            )

        if offer.is_physical and offer.stock < item.quantity:
            raise ValueError(
                f'„{title}“ — მარაგში მხოლოდ '
                f'{offer.stock} ეგზემპლარია.'
            )

        OrderItem.objects.create(
            order=order,
            offer=offer,
            book_title=title,
            format=offer.format,
            unit_price=offer.price,
            quantity=item.quantity,
        )

        total += offer.price * item.quantity

        if offer.is_physical:
            offer.stock -= item.quantity
            offer.save(update_fields=['stock'])

    order.total_amount = total
    order.save(update_fields=['total_amount'])

    # იშლება მხოლოდ შეძენილი ნივთები.
    cart.items.filter(
        pk__in=[item.pk for item in cart_items]
    ).delete()

    return order


# შეკვეთების ისტორია
@login_required
def order_list(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items')
    )

    return render(request, 'books/order_list.html', {
        'orders': orders,
    })


# კონკრეტული შეკვეთის დეტალები
@login_required
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        pk=order_id,
        user=request.user,
    )

    return render(request, 'books/order_detail.html', {
        'order': order,
    })



@login_required
def download_ebook(request, order_item_id):
    item = get_object_or_404(
        OrderItem.objects.select_related('order', 'offer'),
        pk=order_item_id,
        order__user=request.user,
        format=BookOffer.Format.DIGITAL,
    )

    if (
        item.order.status == Order.Status.CANCELLED
        or item.order.payment_status != Order.PaymentStatus.PAID
        or not item.offer.ebook_file
    ):
        raise Http404('ფაილი მიუწვდომელია.')

    try:
        file_handle = item.offer.ebook_file.open('rb')
    except (FileNotFoundError, OSError, ValueError):
        raise Http404('PDF ფაილი ვერ მოიძებნა.')

    filename = Path(item.offer.ebook_file.name).name

    return FileResponse(
        file_handle,
        as_attachment=True,
        filename=filename,
        content_type='application/pdf',
    )


# პროფილი
@login_required
def profile(request):
    form = ProfileForm(
        request.POST or None,
        instance=request.user,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()

        messages.success(request, 'პროფილი განახლდა.')

        return redirect('books:profile')

    return render(request, 'books/profile.html', {
        'form': form,
        'orders_count': Order.objects.filter(
            user=request.user
        ).count(),
    })
