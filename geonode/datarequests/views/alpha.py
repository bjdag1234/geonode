import os
import sys
import shutil
import traceback
import datetime
import time
import csv
from urlparse import parse_qs

from crispy_forms.utils import render_crispy_form

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import (
    redirect, get_object_or_404, render, render_to_response)
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.template.response import TemplateResponse
from django.utils import dateformat
from django.utils import timezone
from django.utils import simplejson as json
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from geonode.base.enumerations import CHARSETS
from geonode.cephgeo.models import UserJurisdiction
from geonode.documents.models import get_related_documents
from geonode.documents.models import Document
from geonode.layers.models import UploadSession, Style
from geonode.layers.utils import file_upload
from geonode.people.models import Profile
from geonode.people.views import profile_detail
from geonode.security.views import _perms_info_json
from geonode.tasks.jurisdiction import place_name_update, jurisdiction_style
from geonode.tasks.jurisdiction2 import compute_size_update, assign_grid_refs, assign_grid_refs_all
from geonode.tasks.requests import migrate_all
from geonode.utils import default_map_config
from geonode.utils import GXPLayer
from geonode.utils import GXPMap
from geonode.utils import llbbox_to_mercator
from geonode.utils import build_social_links

from geoserver.catalog import Catalog

from unidecode import unidecode
from pprint import pprint


from braces.views import (
    SuperuserRequiredMixin, LoginRequiredMixin,
)

from geonode.datarequests.forms import (
    ProfileRequestForm, DataRequestShapefileForm,
    RejectionForm, DataRequestForm)

from geonode.datarequests.models import DataRequestProfile, DataRequest, ProfileRequest

from geonode.datarequests.utils import (
    get_place_name, get_area_coverage)

@login_required
def requests_landing(request):
    """Renders the homepage for datarequests

    If user is a superuser, this function displays the requests home page, /requests, else this function displays the data requests of the user, /requests/data.

    URL:
        url(r'^/?$','requests_landing',name='requests_landing'),

    """
    if request.user.is_superuser:
        return TemplateResponse(request, 'datarequests/requests_landing.html',{}, status=200).render()
    else:
        return HttpResponseRedirect(reverse('datarequests:data_request_browse'))

@login_required
def requests_csv(request):
    """Creates a csv tabulating ProfileRequest and DataRequest

    This function produces the CSV file download of all profile and data requests when the Download CSV button in the requests home page has been clicked.

    URL:
        url(r'^requests_csv/$','requests_csv',name='requests_csv'),

    Returns:
        csv file: named 'requests-<month><day><year>'.
            `header_fields`: First row content
            `profile_request_fields`: ProfileRequest keys to be placed on each column per object
            `data_request_fields`: DataRequest keys to be placed on each column per object

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect("/forbidden")
    else:
        response = HttpResponse(content_type='text/csv')
        datetoday = timezone.now()
        response['Content-Disposition'] = 'attachment; filename="requests-"'+str(datetoday.month)+str(datetoday.day)+str(datetoday.year)+'.csv"'

        writer = csv.writer(response)
        header_fields = ['name','email','contact_number', 'organization', 'organization_type','organization_other', 'created','status','has_data_request','data_request_status','area_coverage','estimated_data_size', ]
        writer.writerow(header_fields)

        ### List all ProfileRequest objects
        objects = ProfileRequest.objects.all().order_by('pk')
        profile_request_fields = ['name','email','contact_number', 'organization', 'organization_type','organization_other', 'created','status', 'has_data_request','data_request_status','area_coverage','estimated_data_size'] #ProfileRequest fields to be displayed.
        for o in objects:
            writer.writerow(o.to_values_list(profile_request_fields)) #returns a list which contains the values of the object (o) with the argument(profile_request_fields) as keys

        ### List all DataRequest objects
        objects = DataRequest.objects.filter(profile_request = None).order_by('pk')
        data_request_fields = ['name', 'email', 'organization','organization_type','organization_other','created','profile_request_status','has_data_request','status','area_coverage','estimated_data_size'] #DataRequest fields to be displayed.
        for o in objects:
            writer.writerow(o.to_values_list(data_request_fields)) #returns a list which contains the values of the object (o) with the argument(data_request_fields) as keys

        return response

class DataRequestProfileList(LoginRequiredMixin, TemplateView):
    """Creats a view for all DataRequestProfile objects

    This class is a TemplateView used to display the old list of submitted combined profile and data requests.

    URL:
        url(r'^old_requests/$',DataRequestProfileList.as_view(),name='old_request_model_view'),

    """
    template_name = 'datarequests/old_requests_model_list.html'
    raise_exception = True

@login_required
def old_requests_csv(request):
    """[Deprecated] Creates a csv tabulating DataRequestProfile

    This function produces a CSV file download of the deprecated data request profile.

    URL:
        url(r'^old_requests/csv$','old_requests_csv',name='old_requests_csv'),

    Function:
        models/profile_request.py's to_values_list(`param1`): Returns a list which contains the values of the object with the argument(`param1) as keys
        models/data_request.py's to_values_list(`param1`): Returns a list which contains the values of the object with the argument(`param1) as keys

    Returns:
        csv file: named 'oldrequests-<month><day><year>'
            `header_fields`: First row content, and keys to be placed on each column per object

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect("/forbidden")

    response = HttpResponse(content_type='text/csv')
    datetoday = timezone.now()
    writer = csv.writer(response)
    response['Content-Disposition'] = 'attachment; filename="oldrequests-"'+str(datetoday.month)+str(datetoday.day)+str(datetoday.year)+'.csv"'
    header_fields = ['id','name','email','contact_number', 'organization', 'project_summary', 'created','request_status', 'org_type'] #DataRequestProfile fields to be displayed
    writer.writerow(header_fields)
    ### List all DataRequestProfile objects
    objects = DataRequestProfile.objects.all().order_by('pk')
    for o in objects:
        writer.writerow(o.to_values_list(header_fields)) #returns a list which contains the values of the object (o) with the argument(header_fields) as keys

    return response

@login_required
def old_request_detail(request, pk,template="datarequests/old_request_detail.html"):
    """Renders the per object DataRequestProfile page

    This function provides a detailed view of a data request profile. The different fields displayed is shown in the `template`, while the configuration for the mini map and `context_dict` parameters, to be used in the `template`, are shown in the function.

    URL:
        url(r'^old_requests/(?P<pk>\d+)/$', 'old_request_detail', name="old_request_detail"),

    Args:
        `pk`(int): primary key of the DataRequestProfile object.
        `template`(string): indicates the template file to be used for displaying the data request profile.

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect("/forbidden")

    request_profile = get_object_or_404(DataRequestProfile, pk=pk)

    if not request.user.is_superuser and not request_profile.profile == request.user:
        raise PermissionDenied

    context_dict={"request_profile": request_profile}

    if request_profile.jurisdiction_shapefile:
        layer = request_profile.jurisdiction_shapefile
        ### assert False, str(layer_bbox)
        config = layer.attribute_config()
        ### Add required parameters for GXP lazy-loading
        layer_bbox = layer.bbox
        bbox = [float(coord) for coord in list(layer_bbox[0:4])]
        srid = layer.srid
        ### Transform WGS84 to Mercator.
        config["srs"] = srid if srid != "EPSG:4326" else "EPSG:900913"
        config["bbox"] = llbbox_to_mercator([float(coord) for coord in bbox])
        config["title"] = layer.title
        config["queryable"] = True

        if layer.storeType == "remoteStore":
            service = layer.service
            source_params = {
                "ptype": service.ptype,
                "remote": True,
                "url": service.base_url,
                "name": service.name}
            maplayer = GXPLayer(
                name=layer.typename,
                ows_url=layer.ows_url,
                layer_params=json.dumps(config),
                source_params=json.dumps(source_params))
        else:
            maplayer = GXPLayer(
                name=layer.typename,
                ows_url=layer.ows_url,
                layer_params=json.dumps(config))

        ### Center/zoom don't matter; the viewer will center on the layer bounds
        map_obj = GXPMap(projection="EPSG:900913")
        NON_WMS_BASE_LAYERS = [
            la for la in default_map_config()[1] if la.ows_url is None]

        metadata = layer.link_set.metadata().filter(
            name__in=settings.DOWNLOAD_FORMATS_METADATA)

        context_dict ["resource"] = layer
        context_dict ["permissions_json"] = _perms_info_json(layer)
        context_dict ["documents"] = get_related_documents(layer)
        context_dict ["metadata"] =  metadata
        context_dict ["is_layer"] = True
        context_dict ["wps_enabled"] = settings.OGC_SERVER['default']['WPS_ENABLED'],

        context_dict["viewer"] = json.dumps(
            map_obj.viewer_json(request.user, * (NON_WMS_BASE_LAYERS + [maplayer])))
        context_dict["preview"] = getattr(
            settings,
            'LAYER_PREVIEW_LIBRARY',
            'leaflet')

        if request.user.has_perm('download_resourcebase', layer.get_self_resource()):
            if layer.storeType == 'dataStore':
                links = layer.link_set.download().filter(
                    name__in=settings.DOWNLOAD_FORMATS_VECTOR)
            else:
                links = layer.link_set.download().filter(
                    name__in=settings.DOWNLOAD_FORMATS_RASTER)
            context_dict["links"] = links

        if settings.SOCIAL_ORIGINS:
            context_dict["social_links"] = build_social_links(request, layer)

    return render_to_response(template, RequestContext(request, context_dict))


@login_required
def old_request_migration(request, pk):
    """Migrates DataRequestProfile object to ProfileRequest and DataRequest

    This function triggers the migration process for the data request profile with primary key `pk`. Migration process is declared in models/data_request_profile.py.

    URL:
        url(r'^old_requests/(?P<pk>\d+)/migrate/$','old_request_migration', name='old_request_migration'),

    Function:
        models/data_request_profile.py's migrate_request_profile(): Migrates the object to ProfileRequest
        models/data_request_profile.py's migrate_request_data(): Migrates the object to DataRequest

    Args:
        `pk`(int): primary key of the DataRequestProfile object.

    Raises:
        'This request has already been migrated...': If the DataRequestProfile already has a profile_request value

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect("/forbidden")

    old_request = get_object_or_404(DataRequestProfile, pk=pk)

    message = ""
    ### Check if DataRequestProfile object already has a profile_request tagged to it
    if old_request.profile_request:
        message += "This request has already been migrated."
        message += "<br/>Profile request: <a href = {}>#{}</a>".format(old_request.profile_request.get_absolute_url(), old_request.profile_request.pk)
        if old_request.data_request:
            message += "<br/>Data request: <a href = {}>{}</a>".format(old_request.data_request.get_absolute_url(), old_request.data_request.pk)
    else:
        ### Migrate DataRequestProfile object to ProfileRequest
        profile_request = old_request.migrate_request_profile()
        ### Check if migration is successful
        if profile_request:
            message += "Migrated profile request can be found here: <a href = {}>{}</a>.".format(profile_request.get_absolute_url(), old_request.profile_request.pk)
            ### Migrate DataRequestProfile object to DataRequest
            data_request = old_request.migrate_request_data()
            ### Check if migration is successful
            if data_request:
                message += "\nMigrated data request can be found here: <a href = {}>{}</a>.".format(data_request.get_absolute_url(), old_request.data_request.pk)
        else:
            message += "Unable to migrate"

    messages.info(request, mark_safe(message))
    return HttpResponseRedirect(reverse('datarequests:old_request_detail', args=[pk]))

@login_required
def old_request_migration_all(request):
    """Migrates all DataRequestProfile object to ProfileRequest and DataRequest

    This function triggers the migration process for all the data request profile objects.

    URL:
        url(r'^old_requests/migrate/$','old_request_migration_all',name='old_request_migration_all'),

    Function:
        ../tasks/requests.py's migrate_all: Migrates all DataRequestProfile using models/data_request_profile.py's migrate_request_profile() and migrate_request_data():

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect("/forbidden")

    ### Run command in celery for it to be asynchronous
    migrate_all.delay()
    messages.info(request, "Old data request profiles are now being migrated. This may take some time.")
    return HttpResponseRedirect(reverse("datarequests:old_request_model_view"))


def old_request_facet_count(request):
    """Number of request per status to be used in html and js

    This function returns with the number of requests per status in JSON format.

    URL:
        url(r'^old_requests/~count_facets/$','old_request_facet_count', name='old_request_facet_count'),

    """
    if not request.user.is_superuser:
        raise PermissionDenied

    if not request.method == 'POST':
        raise PermissionDenied

    facets_count = {
        'pending': DataRequestProfile.objects.filter(
            request_status='pending').exclude(date=None).count(),
        'approved': DataRequestProfile.objects.filter(
            request_status='approved').count(),
        'rejected': DataRequestProfile.objects.filter(
            request_status='rejected').count(),
        'cancelled': DataRequestProfile.objects.filter(
            request_status='cancelled').exclude(date=None).count(),
    }

    return HttpResponse(
        json.dumps(facets_count),
        status=200,
        mimetype='text/plain'
    )
