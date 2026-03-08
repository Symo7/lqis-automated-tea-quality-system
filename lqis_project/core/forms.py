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


class FactoryThresholdForm(forms.ModelForm):
    class Meta:
        model = FactoryThreshold
        fields = ["factory", "min_pluck", "max_moisture", "max_foreign_matter"]
