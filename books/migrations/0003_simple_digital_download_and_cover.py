import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0002_seller_order_contact'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bookoffer',
            name='access_type',
        ),
        migrations.AddField(
            model_name='book',
            name='cover_image',
            field=models.ImageField(blank=True, null=True, upload_to='books/covers/', verbose_name='წიგნის ყდა'),
        ),
        migrations.AddField(
            model_name='bookoffer',
            name='ebook_file',
            field=models.FileField(blank=True, help_text='ატვირთეთ მხოლოდ იმ ელექტრონული წიგნის ფაილი, რომლის გავრცელების უფლებაც გაქვთ.', null=True, upload_to='books/ebooks/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf'])], verbose_name='ელექტრონული წიგნის PDF ფაილი'),
        ),
    ]
