from django import forms

from .models import Application


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ("resume", "cover_letter")
        widgets = {"cover_letter": forms.Textarea(attrs={"rows": 5})}