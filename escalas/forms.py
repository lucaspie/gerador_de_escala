from django import forms
from django.db import models

class CriarEscalaForm(forms.Form):
    
    class TipoEscala(models.TextChoices):
        DINAMICA = "DIN", "⚡ Dinâmica (dia a dia)"
        SEMANAL = "SEM", "📅 Fixa semanal"

    tipo_escala = forms.ChoiceField(
        label="Tipo de Escala",
        choices=TipoEscala.choices,
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )
    
    data_inicio = forms.DateField(
        label="Data de início (segunda-feira)",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
            }
        ),
    )

    qtd_madrugada = forms.IntegerField(
        label="Militares por turno (Madrugada)",
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    qtd_noturno = forms.IntegerField(
        label="Militares por turno (Noturno)",
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
