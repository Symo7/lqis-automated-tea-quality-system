from django.contrib import admin

from sampling.models import FactoryIntakeSample, QualityAlert, SampleDecisionHistory


admin.site.register(FactoryIntakeSample)
admin.site.register(QualityAlert)
admin.site.register(SampleDecisionHistory)
