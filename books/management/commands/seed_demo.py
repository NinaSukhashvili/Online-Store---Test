from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from books.models import Author, Book, BookOffer, Category, Publisher, Seller

# მონაცემები: ფასები და გამყიდველები პირობითია.
SELLERS = ['წიგნის სახლი (დემო)', 'ბიბლიო კუთხე (დემო)', 'ციფრული თაროები (დემო)']
PUBLISHER = 'დემო გამომცემლობა'

BOOKS = [
    ('ვეფხისტყაოსანი', 'შოთა რუსთაველი', 'კლასიკა', 1200,
     'XII საუკუნის ქართული პოეზიის შედევრი — ამბავი მეგობრობის, სიყვარულისა და ერთგულების შესახებ.'),
    ('ალუდა ქეთელაური', 'ვაჟა-ფშაველა', 'პოეზია', 1888,
     'ვაჟა-ფშაველას პოემა ადამიანური ღირსებისა და ტრადიციის კონფლიქტზე.'),
    ('კაცია-ადამიანი?!', 'ილია ჭავჭავაძე', 'კლასიკა', 1863,
     'ილია ჭავჭავაძის ცნობილი მოთხრობა.'),
    ('ჯაყოს ხიზნები', 'მიხეილ ჯავახიშვილი', 'რომანი', 1925,
     'XX საუკუნის ქართული პროზის ერთ-ერთი ყველაზე თვალსაჩინო რომანი.'),
    ('მე, ბებია, ილიკო და ილარიონი', 'ნოდარ დუმბაძე', 'რომანი', 1960,
     'თბილი, იუმორით სავსე ამბავი ბავშვობაზე, სიკეთესა და ადამიანურობაზე.'),
    ('დიონისოს ღიმილი', 'კონსტანტინე გამსახურდია', 'რომანი', 1925,
     'კონსტანტინე გამსახურდიას ადრეული მხატვრული პროზა.'),
    ('გზაზე ერთი კაცი მიდიოდა', 'ოთარ ჭილაძე', 'რომანი', 1972,
     'ოთარ ჭილაძის ფილოსოფიური რომანი ადამიანის ბედისა და არჩევანის შესახებ.'),
    ('1984', 'ჯორჯ ორუელი', 'მეცნიერული ფანტასტიკა', 1949,
     'ანტიუტოპიური რომანი ტოტალიტარულ საზოგადოებაზე.'),
]

# (ფორმატი, ფასი, მარაგი, გამყიდველის ინდექსი)
OFFER_PATTERNS = [
    [('physical', '24.00', 12, 0), ('physical', '22.50', 5, 1), ('digital', '12.00', 0, 2)],
    [('physical', '15.00', 8, 1), ('digital', '8.00', 0, 2)],
    [('physical', '18.00', 3, 0), ('digital', '6.00', 0, 2)],
    [('physical', '21.00', 10, 0), ('physical', '19.00', 0, 1)],
    [('physical', '20.00', 15, 1), ('digital', '10.00', 0, 2)],
    [('physical', '23.00', 7, 0)],
    [('physical', '26.00', 4, 1), ('digital', '11.00', 0, 2)],
    [('physical', '28.00', 9, 0), ('digital', '9.00', 0, 2)],
]


class Command(BaseCommand):
    help = 'ამატებს სატესტო წიგნებს, ავტორებს, კატეგორიებსა და შეთავაზებებს.'

    @transaction.atomic
    def handle(self, *args, **options):
        sellers = [Seller.objects.get_or_create(name=n)[0] for n in SELLERS]
        publisher, _ = Publisher.objects.get_or_create(name=PUBLISHER)

        created = 0
        for index, (title, author_name, category_name, year, description) in enumerate(BOOKS):
            author, _ = Author.objects.get_or_create(name=author_name)
            category, _ = Category.objects.get_or_create(name=category_name)

            book, is_new = Book.objects.get_or_create(
                title=title,
                defaults={
                    'description': description,
                    'publication_year': year,
                    'publisher': publisher,
                },
            )
            book.authors.add(author)
            book.categories.add(category)

            if is_new:
                created += 1
                for fmt, price, stock, seller_idx in OFFER_PATTERNS[index]:
                    BookOffer.objects.create(
                        book=book,
                        seller=sellers[seller_idx],
                        format=fmt,
                        price=Decimal(price),
                        stock=stock,
                    )

        self.stdout.write(self.style.SUCCESS(
            f'დასრულდა. დაემატა ახალი წიგნი: {created}. (არსებული წიგნები არ დუბლირდება.)'
        ))
