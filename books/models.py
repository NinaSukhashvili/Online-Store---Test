
from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.validators import (
    FileExtensionValidator,
    MinValueValidator,
    MaxValueValidator,
)


# ავტორის მოდელი
class Author(models.Model):
    name = models.CharField(max_length=150)


    def __str__(self):
        return self.name


# გამომცემლობის მოდელი
class Publisher(models.Model):
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


# კატეგორიის მოდელი
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# გამყიდველის მოდელი
class Seller(models.Model):
    name = models.CharField('სახელი', max_length=150, unique=True)

    class Meta:
        verbose_name = 'გამყიდველი'
        verbose_name_plural = 'გამყიდველები'
        ordering = ['name']

    def __str__(self):
        return self.name


# წიგნის ძირითადი მოდელი
class Book(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    cover_image = models.ImageField(
        'წიგნის ყდა',
        upload_to='books/covers/',
        blank=True,
        null=True
    )

    pages = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    publication_year = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    authors = models.ManyToManyField(
        Author,
        related_name='books'
    )

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books'
    )

    categories = models.ManyToManyField(
        Category,
        related_name='books',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', 'title']

    def __str__(self):
        return self.title


# შეთავაზებების მოთხოვნები
class BookOfferQuerySet(models.QuerySet):

    def purchasable(self):
        """მხოლოდ ის შეთავაზებები, რომელთა ყიდვაც შესაძლებელია."""
        return self.filter(is_available=True).filter(
            Q(format='digital', ebook_file__gt='') |
            Q(format='physical', stock__gt=0)
        )


# წიგნის გაყიდვის შეთავაზება
class BookOffer(models.Model):

    class Format(models.TextChoices):
        PHYSICAL = 'physical', 'ფიზიკური წიგნი'
        DIGITAL = 'digital', 'ელექტრონული წიგნი'

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='offers'
    )

    seller = models.ForeignKey(
        Seller,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offers'
    )

    format = models.CharField(
        max_length=20,
        choices=Format.choices
    )

    ebook_file = models.FileField(
        'ელექტრონული წიგნის PDF ფაილი',
        upload_to='books/ebooks/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        blank=True,
        null=True,
        help_text='ატვირთეთ მხოლოდ იმ ელექტრონული წიგნის ფაილი, რომლის გავრცელების უფლებაც გაქვთ.'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    stock = models.PositiveIntegerField(
        default=0,
        help_text='მარაგის რაოდენობა ფიზიკური წიგნებისთვის'
    )

    is_available = models.BooleanField(default=True)

    objects = BookOfferQuerySet.as_manager()

    class Meta:
        ordering = ['price']

    @property
    def is_physical(self):
        return self.format == self.Format.PHYSICAL

    @property
    def is_digital(self):
        return self.format == self.Format.DIGITAL

    @property
    def is_purchasable(self):
        if not self.is_available:
            return False
        if self.is_physical:
            return self.stock > 0
        return bool(self.ebook_file)

    @property
    def max_quantity(self):
        """ციფრული წიგნი მხოლოდ ერთი ეგზემპლარით იყიდება."""
        return self.stock if self.is_physical else 1

    def __str__(self):
        return f'{self.book.title} - {self.get_format_display()}'


# მომხმარებლის კალათა
class Cart(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'კალათა - {self.user}'

    @property
    def total(self):
        return sum(
            (item.total_price for item in self.items.select_related('offer')),
            Decimal('0.00')
        )


# კალათის პროდუქტები
class CartItem(models.Model):

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )

    offer = models.ForeignKey(
        BookOffer,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'offer'],
                name='unique_offer_in_cart'
            )
        ]

    def __str__(self):
        return f'{self.offer.book.title} x {self.quantity}'

    @property
    def total_price(self):
        return self.offer.price * self.quantity


# შეკვეთის მოდელი
class Order(models.Model):

    class Status(models.TextChoices):
        PENDING = 'pending', 'მოლოდინში'
        CONFIRMED = 'confirmed', 'დადასტურებული'
        SHIPPED = 'shipped', 'გაგზავნილი'
        COMPLETED = 'completed', 'დასრულებული'
        CANCELLED = 'cancelled', 'გაუქმებული'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'unpaid', 'გადაუხდელი'
        PAID = 'paid', 'გადახდილი'
        FAILED = 'failed', 'წარუმატებელი'
        REFUNDED = 'refunded', 'დაბრუნებული'

    # გადახდის ერთადერთი მეთოდი
    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'საბანკო ბარათი'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CARD
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    full_name = models.CharField(max_length=150, blank=True)

    phone = models.CharField(max_length=30, blank=True)

    shipping_address = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'შეკვეთა #{self.id} - {self.user}'


# შეკვეთის პროდუქტები
class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    offer = models.ForeignKey(
        BookOffer,
        on_delete=models.PROTECT,
        related_name='order_items'
    )

    book_title = models.CharField(max_length=200)

    format = models.CharField(max_length=20)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return f'{self.book_title} x {self.quantity}'

    @property
    def total_price(self):
        return self.unit_price * self.quantity


# წიგნის შეფასება და კომენტარი
class BookReview(models.Model):

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='წიგნი'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='book_reviews',
        verbose_name='მომხმარებელი'
    )

    rating = models.PositiveSmallIntegerField(
    'შეფასება',
    validators=[
        MinValueValidator(1),
        MaxValueValidator(5)
    ],
    blank=True,
    null=True
)

    comment = models.TextField(
        'კომენტარი',
        blank=True
    )

    created_at = models.DateTimeField(
        'შექმნის თარიღი',
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        'განახლების თარიღი',
        auto_now=True
    )

    class Meta:
        verbose_name = 'წიგნის შეფასება'
        verbose_name_plural = 'წიგნების შეფასებები'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['book', 'user'],
                name='unique_user_book_review'
            )
        ]

    def __str__(self):
        return f'{self.book.title} - {self.rating}/5 - {self.user}'
