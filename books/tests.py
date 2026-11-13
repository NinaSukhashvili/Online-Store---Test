from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from .models import Author, Book, BookOffer, Cart, CartItem, Category, Order, Seller

User = get_user_model()


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(name='ტესტ ავტორი')
        cls.category = Category.objects.create(name='რომანი')
        cls.seller = Seller.objects.create(name='ტესტ გამყიდველი')

        cls.book = Book.objects.create(title='ტესტ წიგნი')
        cls.book.authors.add(cls.author)
        cls.book.categories.add(cls.category)

        cls.physical = BookOffer.objects.create(
            book=cls.book, seller=cls.seller, format='physical',
            price=Decimal('20.00'), stock=3,
        )
        cls.digital = BookOffer.objects.create(
            book=cls.book, format='digital', ebook_file='books/ebooks/test-book.pdf',
            price=Decimal('9.50'),
        )

        cls.hidden = Book.objects.create(title='უმარაგო წიგნი')
        cls.hidden.authors.add(cls.author)
        BookOffer.objects.create(
            book=cls.hidden, format='physical', price=Decimal('5.00'), stock=0,
        )

        cls.user = User.objects.create_user('nino', 'nino@example.com', 'StrongPass-123')


class CatalogTests(BaseTestCase):
    def test_home_and_catalog_return_200(self):
        self.assertEqual(self.client.get(reverse('books:home')).status_code, 200)
        self.assertEqual(self.client.get(reverse('books:book_list')).status_code, 200)

    def test_catalog_hides_books_without_stock(self):
        response = self.client.get(reverse('books:book_list'))
        self.assertContains(response, 'ტესტ წიგნი')
        self.assertNotContains(response, 'უმარაგო წიგნი')

    def test_search_by_title_and_author(self):
        url = reverse('books:book_list')
        self.assertContains(self.client.get(url, {'q': 'ტესტ წიგნი'}), 'ტესტ წიგნი')
        self.assertContains(self.client.get(url, {'q': 'ტესტ ავტორი'}), 'ტესტ წიგნი')
        self.assertNotContains(self.client.get(url, {'q': 'არარსებული'}), 'ტესტ წიგნი')

    def test_filters_do_not_crash_on_bad_input(self):
        url = reverse('books:book_list')
        response = self.client.get(url, {
            'category': 'abc', 'format': 'zzz', 'min_price': 'x', 'sort': '???', 'page': '99',
        })
        self.assertEqual(response.status_code, 200)

    def test_price_and_format_filters(self):
        url = reverse('books:book_list')
        self.assertContains(self.client.get(url, {'max_price': '10'}), 'ტესტ წიგნი')
        self.assertNotContains(self.client.get(url, {'min_price': '50'}), 'ტესტ წიგნი')
        self.assertContains(self.client.get(url, {'category': self.category.id}), 'ტესტ წიგნი')

    def test_detail_shows_offers_and_404(self):
        response = self.client.get(reverse('books:book_detail', args=[self.book.id]))
        self.assertContains(response, 'ტესტ გამყიდველი')
        self.assertContains(response, 'ყველაზე იაფი')
        self.assertEqual(self.client.get(reverse('books:book_detail', args=[9999])).status_code, 404)


class AuthTests(BaseTestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse('books:register'), {
            'username': 'new_user', 'email': 'new@example.com',
            'password1': 'VeryStrong-Pass-77', 'password2': 'VeryStrong-Pass-77',
        })
        self.assertRedirects(response, reverse('books:home'))
        self.assertTrue(User.objects.filter(username='new_user').exists())

    def test_duplicate_email_rejected(self):
        response = self.client.post(reverse('books:register'), {
            'username': 'other', 'email': 'NINO@example.com',
            'password1': 'VeryStrong-Pass-77', 'password2': 'VeryStrong-Pass-77',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='other').exists())

    def test_registration_username_is_limited_to_15_characters(self):
        response = self.client.post(reverse('books:register'), {
            'username': 'sixteen_char_name',
            'email': 'longname@example.com',
            'password1': 'VeryStrong-Pass-77',
            'password2': 'VeryStrong-Pass-77',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='longname@example.com').exists())

    def test_login_required_pages_redirect(self):
        for name in ['books:cart', 'books:checkout', 'books:order_list', 'books:profile']:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn('/accounts/login/', response.url)


class CartAndOrderTests(BaseTestCase):
    def setUp(self):
        self.client.force_login(self.user)

    def test_add_to_cart_caps_by_stock(self):
        url = reverse('books:cart_add', args=[self.physical.id])
        self.client.post(url, {'quantity': 2})
        self.client.post(url, {'quantity': 5})
        item = CartItem.objects.get(offer=self.physical)
        self.assertEqual(item.quantity, 3)

    def test_digital_quantity_is_always_one(self):
        self.client.post(reverse('books:cart_add', args=[self.digital.id]), {'quantity': 7})
        self.assertEqual(CartItem.objects.get(offer=self.digital).quantity, 1)

    def test_digital_offer_without_pdf_is_not_purchasable(self):
        offer = BookOffer.objects.create(
            book=self.book, format='digital', price=Decimal('4.00')
        )
        self.assertFalse(offer.is_purchasable)
        self.client.post(reverse('books:cart_add', args=[offer.id]))
        self.assertFalse(CartItem.objects.filter(offer=offer).exists())

    def test_cannot_add_unavailable_offer(self):
        self.physical.stock = 0
        self.physical.save()
        self.client.post(reverse('books:cart_add', args=[self.physical.id]))
        self.assertFalse(CartItem.objects.exists())

    def test_cart_requires_post_for_changes(self):
        self.assertEqual(
            self.client.get(reverse('books:cart_add', args=[self.physical.id])).status_code, 405
        )

    def test_user_cannot_touch_foreign_cart_item(self):
        other = User.objects.create_user('other', 'o@example.com', 'StrongPass-123')
        item = CartItem.objects.create(cart=Cart.objects.create(user=other), offer=self.physical)
        response = self.client.post(reverse('books:cart_remove', args=[item.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=item.pk).exists())

    def test_checkout_creates_order_and_reduces_stock(self):
        self.client.post(reverse('books:cart_add', args=[self.physical.id]), {'quantity': 2})
        self.client.post(reverse('books:cart_add', args=[self.digital.id]))

        response = self.client.post(reverse('books:checkout'), {
            'full_name': 'ნინო ტესტი', 'phone': '+995 555 12 34 56',
            'shipping_address': 'თბილისი, ტესტის ქუჩა 1',
        })
        order = Order.objects.get()
        self.assertRedirects(response, reverse('books:order_detail', args=[order.id]))
        self.assertEqual(order.total_amount, Decimal('49.50'))
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.payment_status, Order.PaymentStatus.UNPAID)

        self.physical.refresh_from_db()
        self.assertEqual(self.physical.stock, 1)
        self.assertFalse(CartItem.objects.exists())

    def test_checkout_requires_address_for_physical(self):
        self.client.post(reverse('books:cart_add', args=[self.physical.id]))
        response = self.client.post(reverse('books:checkout'), {
            'full_name': 'ნინო', 'phone': '555123456', 'shipping_address': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_checkout_digital_only_needs_no_address(self):
        self.client.post(reverse('books:cart_add', args=[self.digital.id]))
        self.client.post(reverse('books:checkout'), {
            'full_name': 'ნინო', 'phone': '555123456',
        })
        self.assertEqual(Order.objects.count(), 1)

    def test_checkout_fails_if_stock_vanished(self):
        self.client.post(reverse('books:cart_add', args=[self.physical.id]), {'quantity': 3})
        BookOffer.objects.filter(pk=self.physical.pk).update(stock=1)
        self.client.post(reverse('books:checkout'), {
            'full_name': 'ნინო', 'phone': '555123456', 'shipping_address': 'მისამართი',
        })
        self.assertFalse(Order.objects.exists())
        self.assertEqual(CartItem.objects.count(), 1)

    def test_digital_download_is_available_only_to_purchasing_user(self):
        self.digital.ebook_file = SimpleUploadedFile(
            'sample.pdf', b'%PDF-1.4 demo file', content_type='application/pdf'
        )
        self.digital.save()
        self.client.post(reverse('books:cart_add', args=[self.digital.id]))
        response = self.client.post(reverse('books:checkout'), {
            'full_name': 'ნინო', 'phone': '555123456',
        })
        order_item = Order.objects.get().items.get()
        download_url = reverse('books:download_ebook', args=[order_item.id])
        self.assertRedirects(response, reverse('books:order_detail', args=[order_item.order_id]))
        detail_response = self.client.get(reverse('books:order_detail', args=[order_item.order_id]))
        self.assertContains(detail_response, 'PDF-ის ჩამოტვირთვა')
        self.assertEqual(self.client.get(download_url).status_code, 200)
        other = User.objects.create_user('other_download', 'other@example.com', 'StrongPass-123')
        self.client.force_login(other)
        self.assertEqual(self.client.get(download_url).status_code, 404)

    def test_users_see_only_their_own_orders(self):
        other = User.objects.create_user('other', 'o@example.com', 'StrongPass-123')
        foreign = Order.objects.create(user=other, total_amount=Decimal('1.00'))
        self.assertEqual(
            self.client.get(reverse('books:order_detail', args=[foreign.id])).status_code, 404
        )

    def test_profile_update(self):
        self.client.post(reverse('books:profile'), {
            'first_name': 'ნინო', 'last_name': 'ტესტი', 'email': 'nino@example.com',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'ნინო')


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command('seed_demo', verbosity=0)
        call_command('seed_demo', verbosity=0)
        self.assertEqual(Book.objects.count(), 8)
        response = self.client.get(reverse('books:book_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ვეფხისტყაოსანი')
