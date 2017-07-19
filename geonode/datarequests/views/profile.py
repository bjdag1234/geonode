from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import (
    redirect, get_object_or_404, render, render_to_response)
from django.template import RequestContext
from django.utils import simplejson as json
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from braces.views import (
    SuperuserRequiredMixin, LoginRequiredMixin,
)

from geonode.people.models import Profile
from geonode.datarequests.forms import RejectionForm
from geonode.datarequests.admin_edit_forms import ProfileRequestEditForm
from geonode.datarequests.models import (
    ProfileRequest, DataRequest, LipadOrgType)

from pprint import pprint
from urlparse import parse_qs

import csv

class ProfileRequestList(LoginRequiredMixin, TemplateView):
    """Creats a view for all ProfileRequest objects

    This class is a TemplateView used to display the list of submitted profile requests.

    URL:
        url(r'^profile/$', ProfileRequestList.as_view(), name='profile_request_browse'),

    """
    template_name = 'datarequests/profile_request_list.html'
    raise_exception = True

@login_required
def profile_request_detail(request, pk, template='datarequests/profile_detail.html'):
    """Renders the per object ProfileRequest page

    This function provides a detailed view of a profile request. The different fields displayed is shown in the `template`, while the `context_dict` parameters, to be used in the `template`, are shown in the function.
    This function imports the RejectionForm to the template. The form is to be used for Rejecting and Canceling of ProfileRequest
    The superuser can view the details of all requests, while the user can only view its own requests.

    URL:
        url(r'^profile/(?P<pk>\d+)/$', 'profile_request_detail', name="profile_request_detail"),

    Args:
        `pk`(int): primary key of the ProfileRequest object.
        `template`(string): indicates the template file to be used for displaying the profile request.

    """
    profile_request = get_object_or_404(ProfileRequest, pk=pk)
    if not request.user.is_superuser and not profile_request.profile == request.user:
        return HttpResponseRedirect('/forbidden')
    pprint("profile_request "+profile_request.status)
    context_dict={"profile_request": profile_request}

    if profile_request.data_request:
        pprint("no data request attached")
        context_dict['data_request'] = profile_request.data_request.get_absolute_url()

    context_dict["request_reject_form"]= RejectionForm(instance=profile_request)

    return render_to_response(template, RequestContext(request, context_dict))

@login_required
def profile_request_edit(request, pk, template ='datarequests/profile_detail_edit.html'):
    """Editing a ProfileRequest object

    This function is for displaying the form for editing the profile request with primary key `pk`. Only admin accounts are allowed to edit it.
    Additionally, editing the email address will cause the profile request to be reset to unconfirmed.
    This is activated by an "Edit Request" button in profile_request_detail with Pending, Unconfirmed Email, Approved, and Rejected Status

    URL:
        url(r'^profile/(?P<pk>\d+)/edit/$', 'profile_request_edit', name="profile_request_edit"),

    Args:
        `pk`(int): primary key of the ProfileRequest object.
        `template`(string): indicates the template file to be used for displaying the profile request.

    Form:
        ProfileRequestEditForm in admin_edit_forms.py

    """
    profile_request = get_object_or_404(ProfileRequest, pk=pk)
    if not  request.user.is_superuser:
        return HttpResponseRedirect('/forbidden')

    if request.method == 'GET':
        context_dict={"profile_request":profile_request}
        context_dict["form"] = ProfileRequestEditForm(initial = model_to_dict(profile_request)) # assign form for editing with initial values, found in admin_edit_forms.py
        return render(request, template, context_dict)
    else: # if POST
        form = ProfileRequestEditForm(request.POST) # assign form
        if form.is_valid():
            pprint("form is valid")
            ### Handle form values
            for k, v in form.cleaned_data.iteritems():
                if k=='org_type':
                    pprint(v)
                    setattr(profile_request, k, v.val) # see declaration of Form for declaration of "val"
                elif k=='email':
                    if form.cleaned_data[k] != profile_request.email and profile_request.status == 'pending' :
                        profile_request.status = 'unconfirmed'
                    setattr(profile_request, k, v)
                else:
                    setattr(profile_request, k, v)
            profile_request.administrator = request.user
            profile_request.save()
        else:
            pprint("form is invalid")
            return render( request, template, {'form': form, 'profile_request': profile_request})
        return HttpResponseRedirect(profile_request.get_absolute_url())

def profile_request_approve(request, pk):
    """Approving a ProfileRequest object

    This is the view function for handling the approval of a profile request. Only requests with status pending can be approved this way. Only superuser can approve requests.
    Upon approval, an AD account and a corresponding FTP directory should be created for the user. The user is then sent an email for him/her to reset his/her password.
    This is activated by an "Approve" button in profile_request_detail with Pending Status

    URL:
        url(r'^profile/(?P<pk>\d+)/approve/$', 'profile_request_approve', name="profile_request_approve"),

    Args:
        `pk`(int): primary key of the ProfileRequest object.

    Function:
        ../models/profile_request.py's ProfileRequest's create_account(self)

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden')
    if not request.method == 'POST':
        return HttpResponseRedirect('/forbidden')

    if request.method == 'POST':
        profile_request = get_object_or_404(ProfileRequest, pk=pk)
        ### Handle errors
        ### If request has not verified his/her email, status should be unconfirmed. Unconfirmed requests cannot be approved
        if not profile_request.has_verified_email:
            if profile_request.status == 'pending':
                profile_request.status = 'unconfirmed'
                profile_request.save()
            messages.info(request,'This request does not have a verified email')
            return HttpResponseRedirect(profile_request.get_absolute_url())
        ### If request's email already in use
        if profile_request.email in Profile.objects.all().values_list('email', flat=True):
            messages.info(request,'The email for this profile request is already in use')
            return HttpResponseRedirect(profile_request.get_absolute_url())
        ### If request status is not pending
        if profile_request.status != 'pending':
            return HttpResponseRedirect('/forbidden')

        result = True
        message = ''

        result, message = profile_request.create_account() #creates account in AD if AD profile does not exist, assigns it to profile_request.profile

        if not result:
            messages.error (request, _(message))
        else:
            ### Get Profile/AD details from ProfileRequest details
            profile_request.profile.organization_type = profile_request.organization_type
            profile_request.profile.org_type = profile_request.org_type
            profile_request.profile.organization_other = profile_request.organization_other
            profile_request.save()
            profile_request.profile.save()
            ### Set request as Approved
            profile_request.set_status('approved',administrator = request.user)
            ### Assign DataRequest's Profile the same Profile assigned to ProfileRequest
            if profile_request.data_request:
                profile_request.data_request.profile = profile_request.profile
                profile_request.data_request.save()
                profile_request.data_request.set_status('pending')
            ### Sends email notification that request is approved
            profile_request.send_approval_email()
        return HttpResponseRedirect(profile_request.get_absolute_url())
    else:
        return HttpResponseRedirect("/forbidden/")

def profile_request_reject(request, pk):
    """Rejecting a ProfileRequest object

    This is the function for handling the rejection of a profile request.
    Only superusers can reject objects.
    This is activated by a "Reject" button in profile_request_detail with Pending Status

    URL:
        url(r'^profile/(?P<pk>\d+)/reject/$', 'profile_request_reject', name="profile_request_reject"),

    Args:
        `pk`(int): primary key of the ProfileRequest object.

    Form:
        forms.py's RejectionForm. See profile_request_detail for importing of the form to the template

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden/')

    if not request.method == 'POST':
         return HttpResponseRedirect('/forbidden/')

    profile_request = get_object_or_404(ProfileRequest, pk=pk)

    if profile_request.status == 'pending':
        form = parse_qs(request.POST.get('form', None))
        profile_request.rejection_reason = form['rejection_reason'][0]
        if 'additional_rejection_reason' in form.keys():
            profile_request.additional_rejection_reason = form['additional_rejection_reason'][0]
        profile_request.save()

        profile_request.set_status('rejected',administrator = request.user)
        profile_request.send_rejection_email()

    url = request.build_absolute_uri(profile_request.get_absolute_url())

    return HttpResponse(
        json.dumps({
            'result': 'success',
            'errors': '',
            'url': url}),
        status=200,
        mimetype='text/plain'
    )

def profile_request_reconfirm(request, pk):
    """Resending a confirmation email to a ProfileRequest object

    This is the function which handles the resending of a confirmation email to a profile request’s email address.
    Only superusers can reconfirm objects.
    This is activated by a "Resend Confirmation Email" button in profile_request_detail with Unconfirmed Email Status

    URL:
        url(r'^profile/(?P<pk>\d+)/reconfirm/$', 'profile_request_reconfirm', name="profile_request_reconfirm"),

    Args:
        `pk`(int): primary key of the ProfileRequest object.

    Function:
        ../models/profile_request.py's ProfileRequest's send_verification_email(self)

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden')

    if not request.method == 'POST':
        return HttpResponseRedirect('/forbidden')

    if request.method == 'POST':
        profile_request = get_object_or_404(ProfileRequest, pk=pk)

        profile_request.send_verification_email()

        messages.info(request, "Confirmation email resent")
        return HttpResponseRedirect(profile_request.get_absolute_url())

def profile_request_recreate_dir(request, pk):
    """Recreating FTP folder of a ProfileRequest object

    This function which executes the creation of an approved account’s FTP folder should it fail.
    Only superusers can reconfirm objects.
    This is activated by a "Create Directory" button in profile_request_detail with Approved Status

    URL:
        url(r'^prolfile/(?P<pk>\d+)/recreate_dir/$', 'profile_request_recreate_dir', name="profile_request_recreate_dir"),

    Args:
        `pk`(int): primary key of the ProfileRequest object.

    Function:
        ../models/profile_request.py's ProfileRequest's create_directory(self)

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden')

    if not request.method == 'POST':
        return HttpResponseRedirect('/forbidden')

    if request.method == 'POST':
        profile_request = get_object_or_404(ProfileRequest, pk=pk)

        profile_request.create_directory()

        messages.info(request, "Folder creation has been scheduled. Check folder location in a few minutes")
        return HttpResponseRedirect(profile_request.get_absolute_url())

def profile_request_cancel(request,pk):
    """Canceling a ProfileRequest object

    This is the function for handling the cancellation of a profile request.
    Only superusers can cancel objects.
    This is activated by a "Cancel Request" button in profile_request_detail with Pending, and Unconfirmed Email Status

    URL:
        url(r'^prolfile/(?P<pk>\d+)/cancel/$', 'profile_request_cancel', name="profile_request_cancel"),

    Args:
        `pk`(int): primary key of the ProfileRequest object.

    Form:
        forms.py's RejectionForm. See profile_request_detail for importing of the form to the template

    """
    profile_request = get_object_or_404(ProfileRequest, pk=pk)
    if not request.user.is_superuser:
        return HttpResponseRedirect('/forbidden')

    if not request.method == 'POST':
        return HttpResponseRedirect('/forbidden')

    if profile_request.status == 'pending' or profile_request.status == 'unconfirmed':
        form = parse_qs(request.POST.get('form', None))
        profile_request.rejection_reason = form['rejection_reason'][0]
        profile_request.save()

        if not request.user.is_superuser:
            profile_request.set_status('cancelled')
        else:
            profile_request.set_status('cancelled',administrator = request.user)

    url = request.build_absolute_uri(profile_request.get_absolute_url())

    return HttpResponse(
        json.dumps({
            'result': 'success',
            'errors': '',
            'url': url}),
        status=200,
        mimetype='text/plain'
    )

@login_required
def profile_requests_csv(request):
    """Creates a csv tabulating ProfileRequest objects

    This function produces the CSV file download of all profile requests when the "Download CSV" button in the ProfileRequestList has been clicked.

    URL:
        url(r'^profile_requests_csv/$', 'profile_requests_csv', name='profile_requests_csv'),

    Returns:
        csv file: named profilerequests-<month><day><year>’.
            `fields`: First row content, and ProfileRequest keys to be placed on each column per object

    """
    if not request.user.is_superuser:
        return HttpResponseRedirect("/forbidden")
    else:
        response = HttpResponse(content_type='text/csv')
        datetoday = timezone.now()
        response['Content-Disposition'] = 'attachment; filename="profilerequests-"'+str(datetoday.month)+str(datetoday.day)+str(datetoday.year)+'.csv"'

        writer = csv.writer(response)
        fields = ['id','name','email','contact_number', 'organization', 'org_type','organization_other', 'created','status', 'status changed','has_data_request', 'place_name', 'area_coverage','estimated_data_size', ]
        writer.writerow( fields)

        objects = ProfileRequest.objects.all().order_by('pk')

        for o in objects:
            writer.writerow(o.to_values_list(fields))

        return response

def profile_request_facet_count(request):
    """Number of request per status to be used in html and js

    This function returns with the number of requests per status in JSON format.

    URL:
        url(r'^profile/~count_facets/$', 'profile_request_facet_count', name="profile_request_facet_count"),

    """

    facets_count = {
        'pending': ProfileRequest.objects.filter(
            status='pending').count(),
        'approved': ProfileRequest.objects.filter(
            status='approved').count(),
        'rejected': ProfileRequest.objects.filter(
            status='rejected').count(),
        'unconfirmed': ProfileRequest.objects.filter(
            status='unconfirmed').count(),
    }

    return HttpResponse(
        json.dumps(facets_count),
        status=200,
        mimetype='text/plain'
    )
