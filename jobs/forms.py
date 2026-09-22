from django import forms

from .models import Job


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = (
            "title",
            "description",
            "requirements",
            "location",
            "employment_type",
            "experience_level",
            "salary_min",
            "salary_max",
            "status",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
            "requirements": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get("salary_min")
        salary_max = cleaned_data.get("salary_max")
        if salary_min and salary_max and salary_min > salary_max:
            self.add_error("salary_max", "Maximum salary must not be less than minimum salary.")
        return cleaned_data