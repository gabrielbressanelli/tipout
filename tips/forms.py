from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Profile, TipEntry


class SignUpForm(UserCreationForm):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone_number = forms.CharField(max_length=15, required=False)

    class Meta:
        model = User
        fields = ('username', 'name', 'email', 'phone_number', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if Profile.objects.filter(email=email).exists() or User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        name = self.cleaned_data['name'].strip()
        user.email = self.cleaned_data['email']
        if ' ' in name:
            user.first_name, user.last_name = name.split(' ', 1)
        else:
            user.first_name = name

        if commit:
            user.save()
            Profile.objects.create(
                user=user,
                system_username=user.username,
                name=name,
                email=user.email,
                phone_number=self.cleaned_data.get('phone_number') or None,
            )
        return user


class TipEntryForm(forms.ModelForm):
    class Meta:
        model = TipEntry
        fields = (
            'service_date',
            'tips_made',
            'total_sales',
            'liquor_sales',
            'beer_sales',
            'wine_sales',
            'assistant_percent',
        )
        widgets = {
            'service_date': forms.DateInput(attrs={'type': 'date'}),
            'assistant_percent': forms.RadioSelect(attrs={'class': 'assistant-choice-input'}),
        }
        labels = {
            'tips_made': 'Tips made',
            'total_sales': 'Food sales',
            'liquor_sales': 'Liquor sales',
            'beer_sales': 'Beer sales',
            'wine_sales': 'Wine sales',
            'assistant_percent': 'Assistant server',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        money_fields = ('tips_made', 'total_sales', 'liquor_sales', 'beer_sales', 'wine_sales')
        for field_name in money_fields:
            self.fields[field_name].widget.attrs.update({
                'inputmode': 'decimal',
                'placeholder': '0.00',
                'step': '0.01',
            })
        self.fields['assistant_percent'].initial = 0


class ProfilePasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        UserModel = get_user_model()
        users = (
            UserModel._default_manager
            .filter(Q(email__iexact=email) | Q(profile__email__iexact=email), is_active=True)
            .distinct()
        )
        return (user for user in users if user.has_usable_password())

    def save(
        self,
        domain_override=None,
        subject_template_name='registration/password_reset_subject.txt',
        email_template_name='registration/password_reset_email.html',
        use_https=False,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        html_email_template_name=None,
        extra_email_context=None,
    ):
        submitted_email = self.cleaned_data['email']
        if not domain_override:
            current_site = get_current_site(request)
            site_name = current_site.name
            domain = current_site.domain
        else:
            site_name = domain = domain_override

        UserModel = get_user_model()
        for user in self.get_users(submitted_email):
            user_pk_bytes = force_bytes(UserModel._meta.pk.value_to_string(user))
            context = {
                'email': submitted_email,
                'domain': domain,
                'site_name': site_name,
                'uid': urlsafe_base64_encode(user_pk_bytes),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
                **(extra_email_context or {}),
            }
            self.send_mail(
                subject_template_name,
                email_template_name,
                context,
                from_email,
                submitted_email,
                html_email_template_name=html_email_template_name,
            )
