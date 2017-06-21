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

class DemCephObjectMapAdmin(admin.ModelAdmin):
    model = DemCephObjectMap

    def get_demdatastore_name(self, obj):
        return obj.demdatastore.name
    get_demdatastore_name.short_description = 'DEM Name'
    get_demdatastore_name.admin_order_field = 'demdatastore__name'

    def get_demdatastore_type(self, obj):
        return obj.demdatastore.type
    get_demdatastore_type.short_description = 'DEM Type'
    get_demdatastore_type.admin_order_field = 'demdatastore__type'
    
    
    def get_cephdataobject_name(self, obj):
        return obj.cephdataobject.name
    get_cephdataobject_name.short_description = 'Ceph Data Object Name'
    get_cephdataobject_name.admin_order_field = 'cephdataobject__name'
    
    def get_lidar_block_name(self, obj):
        return obj.lidar_block.block_name
    get_lidar_block_name.short_description = 'Lidar Block Name'
    get_lidar_block_name.admin_order_field = 'lidar_block__block_name'
    
    list_display_links = ('id',)
    list_display = (
        'id',
        'get_demdatastore_name',
        'get_cephdataobject_name',
        'get_demdatastore_type',
        'get_lidar_block_name',
    )
    search_fields = ('demdatastore__name', 'cephdataobject__name', 'demdatastore__type', 'lidar_block__block_name',)
    list_filter = ('demdatastore__type',)


admin.site.register(AutomationJob, AutomationJobAdmin)
admin.site.register(DemDataStore, DemDataStoreAdmin)
admin.site.register(DemCephObjectMap, DemCephObjectMapAdmin)
