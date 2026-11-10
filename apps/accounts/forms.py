from django import forms
from django.contrib.auth.forms import (
    UserCreationForm,
    UserChangeForm,
)

from .models import User


class CustomUserCreationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
    )

    class Meta(UserCreationForm.Meta):

        model = User

        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
        )

    def clean_email(self):

        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email=email).exists():

            raise forms.ValidationError("An account with this email already exists.")

        return email


class CustomUserChangeForm(UserChangeForm):

    class Meta:

        model = User

        fields = "__all__"
