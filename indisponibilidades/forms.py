# indisponibilidades/forms.py
from django import forms
from .models import Indisponibilidade

class IndisponibilidadeForm(forms.ModelForm):
    class Meta:
        model = Indisponibilidade
        fields = ["data_inicio", "data_fim", "motivo", "observacao"]
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop("usuario", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get("data_inicio")
        fim = cleaned.get("data_fim")

        if not inicio or not fim:
            return cleaned

        conflito = Indisponibilidade.objects.filter(
            usuario=self.usuario,
            data_inicio__lte=fim,
            data_fim__gte=inicio,
        ).exists()

        if conflito:
            raise forms.ValidationError(
                "Você já possui uma indisponibilidade nesse período."
            )

        return cleaned
