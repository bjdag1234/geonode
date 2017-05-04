from django.contrib import admin
from geonode.automation.models import *

# Register your models here.


class AutomationJobAdmin(admin.ModelAdmin):
    model = AutomationJob
    list_display_links = ('id',)
    list_display = (
        'id',
        'datatype',
        'input_dir',
        'processor',
        'date_submitted',
        'status',
    )
    search_fields = ('datatype', 'status', 'input_dir', 'processor')

admin.site.register(AutomationJob, AutomationJobAdmin)
