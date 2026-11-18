
# რეგისტრაციის ფორმა, პროფილის ფორმა, შეკვეთის ფორმა და წიგნის შეფასება

from django.utils.safestring import mark_safe
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import BookReview

User = get_user_model()


class RegisterForm(UserCreationForm):
    """რეგისტრაციის ფორმა: მომხმარებლის სახელი, ელფოსტა და პაროლი."""

    username = forms.CharField(
        label='მომხმარებლის სახელი',
        max_length=15,
        min_length=3,
        required=True,
    )

    email = forms.EmailField(
        label='ელფოსტა',
        required=True,
    )

    class Meta:
        model = User
        fields = ('username', 'email')
        labels = {
            'username': 'მომხმარებლის სახელი',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'პაროლი'
        self.fields['password2'].label = 'გაიმეორეთ პაროლი'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'ამ ელფოსტით მომხმარებელი უკვე რეგისტრირებულია.'
            )

        return email


class ProfileForm(forms.ModelForm):
    """მომხმარებლის პროფილის რედაქტირების ფორმა."""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        labels = {
            'first_name': 'სახელი',
            'last_name': 'გვარი',
            'email': 'ელფოსტა',
        }

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email__iexact=email).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError(
                'ეს ელფოსტა სხვა მომხმარებელს უკვე აქვს.'
            )

        return email


class CheckoutForm(forms.Form):
    """შეკვეთის გაფორმების ფორმა."""

    full_name = forms.CharField(
        label='სახელი და გვარი',
        max_length=150,
        required=True,
    )

    phone = forms.CharField(
        label='ტელეფონი',
        max_length=30,
        required=True,
    )

    shipping_address = forms.CharField(
        label='მისამართი',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, needs_address=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.needs_address = needs_address

        # მისამართი აუცილებელია მხოლოდ მაშინ, როცა კალათაში ფიზიკური წიგნია.
        self.fields['shipping_address'].required = needs_address

        # სავალდებულო ველების წითელი ვარსკვლავით მონიშვნა
        for field in self.fields.values():
            if field.required:
                field.label = mark_safe(
                    f'{field.label} <span class="required-star">*</span>'
                )

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        digits = [c for c in phone if c.isdigit()]
        allowed = set('0123456789+ -()')

        if len(digits) < 9 or not set(phone) <= allowed:
            raise forms.ValidationError(
                'მიუთითეთ სწორი ტელეფონის ნომერი.'
            )

        return phone


class BookReviewForm(forms.ModelForm):
    """წიგნის შეფასებისა და კომენტარის ფორმა."""

    RATING_CHOICES = [
        (5, '★★★★★'),
        (4, '★★★★☆'),
        (3, '★★★☆☆'),
        (2, '★★☆☆☆'),
        (1, '★☆☆☆☆'),
    ]

    rating = forms.ChoiceField(
        label='შეაფასე წიგნი',
        choices=[('', 'შეფასების გარეშე')] + RATING_CHOICES,
        widget=forms.RadioSelect,
        required=False,
    )

    comment = forms.CharField(
        label='შენი კომენტარი',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'გაგვიზიარე შენი შთაბეჭდილება ამ წიგნზე...',
        }),
    )

    class Meta:
        model = BookReview
        fields = ('rating', 'comment')

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')

        if not rating:
            return None

        return int(rating)
