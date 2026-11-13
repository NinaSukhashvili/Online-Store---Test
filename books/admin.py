
from django.contrib import admin
from .models import (
    Author,
    Publisher,
    Seller,
    Category,
    Book,
    BookOffer,
    Cart,
    CartItem,
    Order,
    OrderItem,
)


class BookOfferInline(admin.TabularInline):
    model = BookOffer
    extra = 1


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'publisher', 'created_at')
    search_fields = ('title', 'description', 'authors__name')
    list_filter = ('publisher', 'categories')
    filter_horizontal = ('authors', 'categories')
    readonly_fields = ('created_at',)
    inlines = [BookOfferInline]


@admin.register(BookOffer)
class BookOfferAdmin(admin.ModelAdmin):
    list_display = (
        'book',
        'seller',
        'format',
        'price',
        'stock',
        'is_available',
    )
    list_filter = ('format', 'is_available', 'seller')
    search_fields = ('book__title',)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')
    search_fields = ('user__username', 'user__email')
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'status',
        'payment_status',
        'total_amount',
        'created_at',
    )
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)
    inlines = [OrderItemInline]
    actions = ['mark_confirmed', 'mark_shipped', 'mark_completed', 'mark_cancelled']

    @admin.action(description='სტატუსი: დადასტურებული')
    def mark_confirmed(self, request, queryset):
        queryset.update(status=Order.Status.CONFIRMED)

    @admin.action(description='სტატუსი: გაგზავნილი')
    def mark_shipped(self, request, queryset):
        queryset.update(status=Order.Status.SHIPPED)

    @admin.action(description='სტატუსი: დასრულებული')
    def mark_completed(self, request, queryset):
        queryset.update(status=Order.Status.COMPLETED)

    @admin.action(description='სტატუსი: გაუქმებული')
    def mark_cancelled(self, request, queryset):
        queryset.update(status=Order.Status.CANCELLED)
