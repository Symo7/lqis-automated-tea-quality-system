from django import forms

from .models import Batch, Factory, FactoryThreshold, Supplier, TeaBuyingCenter


class FactoryForm(forms.ModelForm):
    class Meta:
        model = Factory
        fields = ["name", "code", "location", "is_active"]


class TeaBuyingCenterForm(forms.ModelForm):
    class Meta:
        model = TeaBuyingCenter
        fields = ["factory", "name", "code", "location"]


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name", "code", "contact", "is_farmer_group"]


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ["factory", "buying_center", "supplier", "batch_code", "intake_date", "notes"]

    def clean(self):
        cleaned_data = super().clean()
        factory = cleaned_data.get("factory")
        buying_center = cleaned_data.get("buying_center")
        if factory and buying_center and buying_center.factory_id != factory.id:
            self.add_error("buying_center", "Selected buying center does not belong to selected factory.")
        return cleaned_data


class FactoryThresholdForm(forms.ModelForm):
    class Meta:
        model = FactoryThreshold
        fields = ["factory", "min_pluck", "max_moisture", "max_foreign_matter"]
