from django import forms
from django.utils import timezone

from core.models import Batch, Factory, Supplier, TeaBuyingCenter
from sampling.models import FactoryIntakeSample


class FactoryIntakeSampleForm(forms.ModelForm):
    class Meta:
        model = FactoryIntakeSample
        fields = [
            "factory",
            "tea_buying_center",
            "supplier",
            "batch",
            "intake_timestamp",
            "leaf_image",
            "manual_override_pluck_score",
            "moisture_pct",
            "foreign_matter_pct",
            "notes",
        ]
        widgets = {
            "intake_timestamp": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "leaf_image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["intake_timestamp"].initial = timezone.now().strftime("%Y-%m-%dT%H:%M")
        self.fields["tea_buying_center"].queryset = TeaBuyingCenter.objects.none()
        self.fields["batch"].queryset = Batch.objects.none()
        self.fields["supplier"].queryset = Supplier.objects.all()

        factory_id = self.data.get("factory") or self.initial.get("factory")
        if factory_id:
            self.fields["tea_buying_center"].queryset = TeaBuyingCenter.objects.filter(factory_id=factory_id)
            self.fields["batch"].queryset = Batch.objects.filter(factory_id=factory_id)

    def clean(self):
        cleaned_data = super().clean()
        factory: Factory = cleaned_data.get("factory")
        tea_buying_center: TeaBuyingCenter = cleaned_data.get("tea_buying_center")
        batch: Batch = cleaned_data.get("batch")

        if factory and tea_buying_center and tea_buying_center.factory_id != factory.id:
            self.add_error("tea_buying_center", "Selected buying center does not belong to selected factory.")

        if factory and batch and batch.factory_id != factory.id:
            self.add_error("batch", "Selected batch does not belong to selected factory.")
            
        supplier: Supplier = cleaned_data.get("supplier")
        if batch and supplier and batch.supplier_id != supplier.id:
            self.add_error("batch", "Selected batch does not belong to selected supplier.")
            
        if batch and tea_buying_center and batch.buying_center_id != tea_buying_center.id:
            self.add_error("batch", "Selected batch does not belong to selected buying center.")

        # Require leaf_image only if no manual override pluck score is provided
        manual_override = cleaned_data.get("manual_override_pluck_score")
        leaf_image = cleaned_data.get("leaf_image")
        if not manual_override and not leaf_image:
            self.add_error("leaf_image", "A leaf image is required unless a manual override pluck score is provided.")

        return cleaned_data


class SupervisorDecisionForm(forms.ModelForm):
    class Meta:
        model = FactoryIntakeSample
        fields = ["decision", "decision_reason"]
        widgets = {
            "decision_reason": forms.Textarea(attrs={"rows": 3}),
        }
