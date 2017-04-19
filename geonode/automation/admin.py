from django.contrib import admin
from geonode.automation.models import *

# Register your models here.


class AutomationJobAdmin(admin.ModelAdmin):
    model = AutomationJob
    list_display_links = ('id',)
    list_display = (
        'id',
        'datatype',
        'turnover_id',
        'pathname',
        'date_submitted',
        'status',
    )
    search_fields = ('datatype', 'status', 'turnover_id', 'pathname')

admin.site.register(AutomationJob, AutomationJobAdmin)
