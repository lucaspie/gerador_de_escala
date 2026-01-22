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
