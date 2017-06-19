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
        'status_timestamp'
    )
    search_fields = ('datatype', 'status', 'input_dir', 'processor')
    list_filter = ('datatype', 'status', 'processor', 'target_os')

class DemDataStoreAdmin(admin.ModelAdmin):
    model = DemDataStore
    list_display_links = ('demid',)
    list_display = (
        'demid',
        'name',
        'type',
        'dem_file_path',
    )
    search_fields = ('demid', 'name', 'type', 'dem_file_path')
    list_filter = ('type',)

admin.site.register(AutomationJob, AutomationJobAdmin)
admin.site.register(DemDataStore, DemDataStoreAdmin)

