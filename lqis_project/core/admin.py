from django.contrib import admin

from core.models import Batch, Factory, FactoryThreshold, Supplier, TeaBuyingCenter


admin.site.register(Factory)
admin.site.register(TeaBuyingCenter)
admin.site.register(Supplier)
admin.site.register(Batch)
admin.site.register(FactoryThreshold)
