from django import forms

class CriarEscalaForm(forms.Form):
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
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
            }
        ),
    )

    qtd_noturno = forms.IntegerField(
        label="Militares por turno (Noturno)",
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
            }
        ),
    )
