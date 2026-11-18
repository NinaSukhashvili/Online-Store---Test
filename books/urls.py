
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = 'books'

urlpatterns = [
    path('', views.home, name='home'),
    path('books/', views.book_list, name='book_list'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),

    # წიგნის შეფასება და კომენტარი
    path(
        'book/<int:book_id>/review/',
        views.book_review_save,
        name='book_review_save'
    ),
    path(
        'review/<int:review_id>/delete/',
        views.book_review_delete,
        name='book_review_delete'
    ),

    # კალათა და შეკვეთა
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:offer_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),

    # ერთი ნივთის ცალკე შეძენა
    path(
        'checkout/item/<int:item_id>/',
        views.checkout_item,
        name='checkout_item'
    ),

    path('checkout/', views.checkout, name='checkout'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('download/<int:order_item_id>/', views.download_ebook, name='download_ebook'),

    # ანგარიში
    path('accounts/register/', views.register, name='register'),
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(
            template_name='registration/login.html',
            redirect_authenticated_user=True,
        ),
        name='login'
    ),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/profile/', views.profile, name='profile'),
    path(
        'accounts/password/',
        auth_views.PasswordChangeView.as_view(
            template_name='registration/password_change.html',
            success_url=reverse_lazy('books:profile'),
        ),
        name='password_change'
    ),
]
