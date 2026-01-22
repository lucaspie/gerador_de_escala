from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class CriarUsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "secao",
            "papel",
            "cursos",
        ]

        widgets = {
            "cursos": forms.CheckboxSelectMultiple,
        }

class EditarUsuarioForm(forms.ModelForm):
    forcar_troca_senha = forms.BooleanField(
        required=False,
        label="Forçar troca de senha no próximo login",
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "secao",
            "papel",
            "cursos",
        ]

        widgets = {
            "cursos": forms.CheckboxSelectMultiple,
        }