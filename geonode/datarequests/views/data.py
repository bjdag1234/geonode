from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import (
    redirect, get_object_or_404, render, render_to_response)
from django.template import RequestContext
from django.utils import simplejson as json
from django.views.generic import TemplateView

from braces.views import (
    SuperuserRequiredMixin, LoginRequiredMixin,
)

from urlparse import parse_qs

from geonode.cephgeo.models import TileDataClass
from geonode.cephgeo.models import UserJurisdiction
from geonode.datarequests.admin_edit_forms import DataRequestEditForm
from geonode.datarequests.forms import DataRequestRejectForm
from geonode.datarequests.models import DataRequest
from geonode.documents.models import get_related_documents
from geonode.security.views import _perms_info_json
from geonode.tasks.jurisdiction import place_name_update
from geonode.tasks.jurisdiction2 import compute_size_update, assign_grid_refs_all, assign_grid_refs
from geonode.tasks.requests import tag_request_suc
from geonode.utils import default_map_config, resolve_object, llbbox_to_mercator
from geonode.utils import GXPLayer, GXPMap

from pprint import pprint

import csv

@login_required
def data_requests_csv(request):
    """Creates a csv tabulating DataRequest objects

    This function produces the CSV file download of all data requests when the "Download CSV" button in the DataRequestList has been clicked.

    URL:
        url(r'^data/data_requests_csv/$', 'data_requests_csv', name='data_requests_csv'),

    Returns:
        csv file: named datarequests-<month><day><year>’.
            `fields`: First row content, and DataRequest keys to be placed on each column per object

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden')

    response = HttpResponse(content_type='text/csv')
    datetoday = timezone.now()
    response['Content-Disposition'] = 'attachment; filename="datarequests-"'+str(datetoday.month)+str(datetoday.day)+str(datetoday.year)+'.csv"'

    writer = csv.writer(response)
    fields = ['id','name','email','contact_number', 'organization', 'org_type','has_profile_request','has_letter','has_shapefile','project_summary', 'created','status', 'status_changed','rejection_reason','juris_data_size','area_coverage']
    writer.writerow( fields)

    objects = DataRequest.objects.all().order_by('pk')

    for o in objects:
        writer.writerow(o.to_values_list(fields))

    return response

class DataRequestList(LoginRequiredMixin, TemplateView):
    """Creats a view for all DataRequest objects

    This class is a TemplateView used to display the list of submitted data requests.

    URL:
        url(r'^data/$', DataRequestList.as_view(), name='data_request_browse'),

    """
    template_name = 'datarequests/data_request_list.html'
    raise_exception = True

@login_required
def user_data_request_list(request):
    data_requests = DataRequest.objects.filter(profile=request.user)

    return None

def data_request_detail(request, pk, template='datarequests/data_detail.html'):
    """Renders the per object DataRequest page

    This function provides a detailed view of a data request. The different fields displayed is shown in the `template`, while the configuration for the mini map and `context_dict` parameters, to be used in the `template`, are shown in the function.
    This function imports the DataRequestRejectForm to the template. The form is to be used for Rejecting and Canceling of DataRequest.
    The superuser can view the details of all requests, while the user can only view its own requests.

    URL:
        url(r'^data/(?P<pk>\d+)/$', 'data_request_detail', name="data_request_detail"),

    Args:
        `pk`(int): primary key of the DataRequest object.
        `template`(string): indicates the template file to be used for displaying the data request.

    """
    data_request = get_object_or_404(DataRequest, pk=pk)

    if not request.user.is_superuser and not data_request.profile == request.user:
        return HttpResponseRedirect('/forbidden')

    context_dict={"data_request": data_request}
    context_dict['data_types'] = data_request.data_type.names()
    context_dict['sucs']=data_request.suc.names()
    context_dict['max_ftp_size']=settings.MAX_FTP_SIZE
    pprint(context_dict ['sucs'])
    pprint("dr.pk="+str(data_request.pk))

    if data_request.profile:
        context_dict['profile'] = data_request.profile

    if data_request.profile_request:
        context_dict['profile_request'] = data_request.profile_request

    if data_request.jurisdiction_shapefile:
         layer = data_request.jurisdiction_shapefile
         # assert False, str(layer_bbox)
         config = layer.attribute_config()
         # Add required parameters for GXP lazy-loading
         layer_bbox = layer.bbox
         bbox = [float(coord) for coord in list(layer_bbox[0:4])]
         srid = layer.srid

         # Transform WGS84 to Mercator.
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

         # center/zoom don't matter; the viewer will center on the layer bounds
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

    context_dict["request_reject_form"]= DataRequestRejectForm(instance=data_request)

    return render_to_response(template, RequestContext(request, context_dict))

@login_required
def data_request_edit(request, pk, template ='datarequests/data_detail_edit.html'):
    """Editing a DataRequest object

    This function is for displaying the form for editing the data request with primary key `pk`. Only admin accounts are allowed to edit it.
    This is activated by an "Edit Request" button in data_request_detail with Pending, Unconfirmed Email, Approved, and Rejected Status

    URL:
        url(r'^data/(?P<pk>\d+)/edit/$', 'data_request_edit', name="data_request_edit"),

    Args:
        `pk`(int): primary key of the DataRequest object.
        `template`(string): indicates the template file to be used for displaying the data request.

    Form:
        DataRequestEditForm in admin_edit_forms.py

    """
    data_request = get_object_or_404(DataRequest, pk=pk)
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden')

    if request.method == 'GET':
        context_dict={"data_request":data_request}
        initial_data = model_to_dict(data_request)
        if not DataRequestEditForm.INTENDED_USE_CHOICES.__contains__(initial_data['purpose']):
            initial_data['purpose_other'] = initial_data['purpose']
            initial_data['purpose'] = 'other'

        context_dict["form"] = DataRequestEditForm(initial = initial_data)
        return render(request, template, context_dict)
    else: # If POST
        form = DataRequestEditForm(request.POST)
        if form.is_valid():
            pprint("form is valid")
            for k, v in form.cleaned_data.iteritems():
                if k == 'data_class_requested':
                    data_types = []
                    data_request.data_type.clear()
                    for i in v:
                        data_request.data_type.add(str(i.short_name)) #short_name found in cephgeo/models.py's TileDataClass
                    #remove original tags
                elif k=='purpose':
                    if v == form.INTENDED_USE_CHOICES.other:
                        setattr(data_request,k,form.cleaned_data.get('purpose_other'))
                    else:
                        setattr(data_request,k,v)
                else:
                    setattr(data_request, k, v)
            data_request.administrator = request.user
            data_request.save()
        else:
            pprint("form is invalid")
            pprint(form.errors)
            return render( request, template, {'form': form, 'data_request': data_request})
        return HttpResponseRedirect(data_request.get_absolute_url())

def data_request_cancel(request, pk):
    """Canceling a DataRequest object

    This is the function for handling the cancellation of a data request.
    Only superusers can cancel objects.
    This is activated by a "Cancel Request" button in data_request_detail with Pending, and Unconfirmed Email Status

    URL:
        url(r'^data/(?P<pk>\d+)/cancel/$', 'data_request_cancel', name="data_request_cancel"),

    Args:
        `pk`(int): primary key of the DataRequest object.

    Form:
        forms.py's DataRequestRejectForm. See data_request_detail for importing of the form to the template

    """
    data_request = get_object_or_404(DataRequest, pk=pk)
    if not request.user.is_superuser and not data_request.profile == request.user:
        return HttpResponseRedirect('/forbidden')

    if not request.method == 'POST':
        pprint("user is not an HTTP POST")
        return HttpResponseRedirect('/forbidden')

    if data_request.status == 'pending':
        form = parse_qs(request.POST.get('form', None))
        data_request.rejection_reason = form['rejection_reason'][0]
        data_request.save()

        if not request.user.is_superuser:
            data_request.set_status('cancelled')
        else:
            data_request.set_status('cancelled',administrator = request.user)

    url = request.build_absolute_uri(data_request.get_absolute_url())

    return HttpResponse(
        json.dumps({
            'result': 'success',
            'errors': '',
            'url': url}),
        status=200,
        mimetype='text/plain'
    )

def data_request_approve(request, pk):
    """Approving a DataRequest object

    This is the view function for handling the approval of a data request. Only requests with status pending, and an AD/Profile/Approved ProfileRequest can be approved this way. Only superuser can approve requests.
    Upon approval, if the data request has a shapefile, the user jurisdiction and grid refs are automatically calculated and assigned. Previous user jurisdiction and assigned grid refs will be overwritten.  The user is then sent an email stating his approval.
    This is activated by an "Approve" button in data_request_detail with Pending Status

    URL:
        url(r'^data/(?P<pk>\d+)/approve/$', 'data_request_approve', name="data_request_approve"),

    Args:
        `pk`(int): primary key of the DataRequest object.

    Function:
        ../models/data_request.py's DataRequest's create_account(self)

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden')
    if not request.method == 'POST':
        return HttpResponseRedirect('/forbidden')

    if request.method == 'POST':
        data_request = get_object_or_404(DataRequest, pk=pk)
        ### Check for an AD/Profile/Approved ProfileRequest
        if not data_request.profile:
            if data_request.profile_request:
                if not data_request.profile_request.status == 'approved':
                    messages.info(request, "Data request #"+str(pk)+" cannot be approved because the requester does not have an approved user yet.")
                    return HttpResponseRedirect(data_request.get_absolute_url())
                    #return HttpResponseRedirect('/forbidden')
                else:
                    data_request.profile = profile_request.profile
                    data_request.save()

        if data_request.jurisdiction_shapefile:# with shapefile
            data_request.assign_jurisdiction() #assigns/creates jurisdiction object
            assign_grid_refs.delay(data_request.profile) #assigns/creates grid_ref object
        else:# No shapefile
            try:
                uj = UserJurisdiction.objects.get(user=data_request.profile)
                uj.delete()
            except ObjectDoesNotExist as e:
                pprint("Jurisdiction Shapefile not found, nothing to delete. Carry on")

        data_request.set_status('approved',administrator = request.user)
        data_request.send_approval_email(data_request.profile.username)
        messages.info(request, "Request "+str(pk)+" has been approved.")

        return HttpResponseRedirect(data_request.get_absolute_url())

    else:
        return HttpResponseRedirect("/forbidden/")

def data_request_reject(request, pk):
    """Rejecting a DataRequest object

    This is the function for handling the rejection of a data request.
    Only superusers can reject objects.
    This is activated by a "Reject" button in data_request_detail with Pending Status

    URL:
        url(r'^data/(?P<pk>\d+)/reject/$', 'data_request_reject', name="data_request_reject"),

    Args:
        `pk`(int): primary key of the DataRequest object.

    Form:
        forms.py's DataRequestRejectForm. See data_request_detail for importing of the form to the template

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden/')

    if not request.method == 'POST':
         return HttpResponseRedirect('/forbidden/')

    data_request = get_object_or_404(DataRequest, pk=pk)

    if data_request.status == 'pending':
        form = parse_qs(request.POST.get('form', None))
        data_request.rejection_reason = form['rejection_reason'][0]
        if 'additional_rejection_reason' in form.keys():
            data_request.additional_rejection_reason = form['additional_rejection_reason'][0]
        data_request.save()

        data_request.set_status('rejected',administrator = request.user)
        data_request.send_rejection_email()

    url = request.build_absolute_uri(data_request.get_absolute_url())

    return HttpResponse(
        json.dumps({
            'result': 'success',
            'errors': '',
            'url': url}),
        status=200,
        mimetype='text/plain'
    )

def data_request_compute_size_all(request):
    """Compute data size and area coverage

    Triggers the size computation (data size and area coverage) in the background for all submitted data request.

    """
    if request.user.is_superuser:
        data_requests = DataRequest.objects.exclude(jurisdiction_shapefile=None)
        compute_size_update.delay(data_requests)
        messages.info(request, "The estimated data size area coverage of the requests are currently being computed")
        return HttpResponseRedirect(reverse('datarequests:data_request_browse'))
    else:
        return HttpResponseRedirect('/forbidden')


def data_request_compute_size(request, pk):
    """

    Triggers the size computation (data size and area coverage) in the background for the data request with primary key pk

    """
    if request.user.is_superuser and request.method == 'POST':
        if DataRequest.objects.get(pk=pk).jurisdiction_shapefile:
            data_requests = DataRequest.objects.filter(pk=pk)
            compute_size_update.delay(data_requests)
            messages.info(request, "The estimated data size area coverage of the request is currently being computed")
        else:
            messages.info(request, "This request does not have a shape file")

        return HttpResponseRedirect(reverse('datarequests:data_request_browse'))
    else:
        return HttpResponseRedirect('/forbidden/')

def data_request_tag_suc_all(request):
    """

    Triggers tagging of all data requests by SUC/HEI

    """
    if request.user.is_superuser:
        drs = DataRequest.objects.exclude(jurisdiction_shapefile=None)
        if drs.count()>0:
            tag_request_suc.delay(drs)
            messages.info(request,"The requests are currently being tagged")
        else:
            messages.info(request,"No request has a shapefile")

        return HttpResponseRedirect(reverse('datarequests:data_request_browse'))
    else:
        return  HttpResponseRedirect('/forbidden/')

def data_request_tag_suc(request,pk):
    """

    Triggers tagging by SUC/HEI of data request with primary key pk

    """
    if request.user.is_superuser and request.method=='POST':
        dr = get_object_or_404(DataRequest, pk=pk)
        if dr.jurisdiction_shapefile:
            tag_request_suc.delay([dr])
            messages.info(request,"This request is currently being tagged")
        else:
            messages.info(request,"This request does not have a shapefile")

        return HttpResponseRedirect(dr.get_absolute_url())
    else:
        return  HttpResponseRedirect('/forbidden/')

def data_request_notify_suc(request,pk):
    """

    Triggers notification of SUC via email regarding request forwarding. Requires an approved data request. If multiple SUCs/HEIs are tagged, notification will be sent to UPD

    """
    if request.user.is_superuser and request.method=='POST':
        dr = get_object_or_404(DataRequest, pk=pk)
        if dr.juris_data_size > settings.MAX_FTP_SIZE:
            dr.send_suc_notification()
            dr.suc_notified=True
            dr.suc_notified_date=timezone.now()
            dr.save()
            messages.info(request, "Email sent")
        return HttpResponseRedirect(dr.get_absolute_url())
    else:
        return HttpResponseRedirect('/forbidden/')

def data_request_notify_requester(request,pk):
    """

    Triggers notification of data requester via email regarding request forwarding. Requires an approved data request

    """
    if request.user.is_superuser and request.method=='POST':
        dr = get_object_or_404(DataRequest, pk=pk)
        dr.notify_user_preforward()
        messages.info(request, "Email sent")
        return HttpResponseRedirect(dr.get_absolute_url())
    else:
        return HttpResponseRedirect('/forbidden/')

def data_request_forward_request(request,pk):
    """

    Triggers forwarding of data request’s shapefile to the tagged SUC/HEI. If multiple SUCs/HEIs are tagged, forwarding will be sent to UPD. Requires an approved data request and notified parties.

    """
    if request.user.is_superuser and request.method=='POST':
        dr = get_object_or_404(DataRequest, pk=pk)
        dr.send_jurisdiction()
        messages.info(request, "Shapefile link sent")
        return HttpResponseRedirect(dr.get_absolute_url())
    else:
        return HttpResponseRedirect('/forbidden/')


def data_request_reverse_geocode_all(request):
    """

    Triggers reverse geocoding for all data requests with a shapefile.

    """
    if request.user.is_superuser:
        data_requests = DataRequest.objects.exclude(jurisdiction_shapefile=None)
        place_name_update.delay(data_requests)
        messages.info(request,"Retrieving approximated place names of data requests")
        return HttpResponseRedirect(reverse('datarequests:data_request_browse'))
    else:
        return HttpResponseRedirect('/forbidden/')

def data_request_reverse_geocode(request, pk):
    """

    Triggers reverse geocoding for a single data request with a shapefile

    """
    if request.user.is_superuser and request.method == 'POST':
        if DataRequest.objects.get(pk=pk).jurisdiction_shapefile:
            data_requests = DataRequest.objects.filter(pk=pk)
            place_name_update.delay(data_requests)
            messages.info(request, "Retrieving approximated place names of data request")
        else:
            messages.info(request, "This request does not have a shape file")

        return HttpResponseRedirect(reverse('datarequests:data_request_browse'))
    else:
        return HttpResponseRedirect('/forbidden/')

def data_request_assign_gridrefs(request):
    """

    Handle assignment of grid refs to users with approved data requests. Doing so will overwrite all existing grid refs assignment

    """
    if request.user.is_superuser:
        assign_grid_refs_all.delay()
        messages.info(request, "Now processing jurisdictions. Please wait for a few minutes for them to finish")
        return HttpResponseRedirect(reverse('datarequests:data_request_browse'))

    else:
        return HttpResponseRedirect('/forbidden/')

def data_request_facet_count(request):
    """Number of request per status to be used in html and js

    This function returns with the number of requests per status in JSON format.

    URL:
        url(r'^data/~count_facets/$', 'data_request_facet_count', name="data_request_facet_count"),

    """
    #if not request.user.is_superuser:
    #    return HttpResponseRedirect('/forbidden')

    if not request.method == 'POST':
        return HttpResponseRedirect('/forbidden')

    facets_count = {}

    if not request.user.is_superuser:
        facets_count = {
            'pending': DataRequest.objects.filter(
                status='pending', profile=request.user).count(),
            'approved': DataRequest.objects.filter(
                status='approved', profile=request.user).count(),
            'rejected': DataRequest.objects.filter(
                status='rejected', profile=request.user).count(),
            'cancelled': DataRequest.objects.filter(
                status='cancelled', profile=request.user).count(),
        }
    else:
        facets_count = {
            'pending': DataRequest.objects.filter(
                status='pending').count(),
            'approved': DataRequest.objects.filter(
                status='approved').count(),
            'rejected': DataRequest.objects.filter(
                status='rejected').count(),
            'cancelled': DataRequest.objects.filter(
                status='cancelled').count(),
        }

    return HttpResponse(
        json.dumps(facets_count),
        status=200,
        mimetype='text/plain'
    )
