from django.conf.urls import url, patterns
import geonode.cephgeo.views as cephgeo_views

urlpatterns = [  # patterns('',
    url(r'^datamanager/automation/$',
        cephgeo_views.automation_trigger),
]  # )
