import ast
import datetime
import os
import shutil
import sys
import traceback

import geonode.settings as settings

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import (
    redirect, get_object_or_404, render, render_to_response)
from django.template.defaultfilters import slugify
from django.utils import dateformat
from django.utils import timezone
from django.utils import simplejson as json
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from geonode.base.enumerations import CHARSETS
from geonode.cephgeo.models import TileDataClass
from geonode.documents.models import Document
from geonode.layers.models import UploadSession, Style
from geonode.layers.utils import file_upload
from geonode.people.models import Profile
from geonode.people.views import profile_detail
from geonode.security.views import _perms_info_json

from geonode.datarequests.forms import (
    ProfileRequestForm, DataRequestForm, DataRequestShapefileForm)

from geonode.datarequests.models import DataRequestProfile, DataRequest, ProfileRequest, BaseRequest

from geonode.tasks.jurisdiction import place_name_update, jurisdiction_style
from geonode.tasks.jurisdiction2 import compute_size_update
from geonode.tasks.requests import set_status_for_multiple_requests, tag_request_suc

from pprint import pprint
from unidecode import unidecode

def register(request):
    """Redirects to profile_request_form

    This function is for handling /register URL. It simply redirects to the profile request URL.

    URL:
        url(r'^register/$','register',name='request_register'),

    """
    return HttpResponseRedirect(
        reverse('datarequests:profile_request_form'))

def profile_request_view(request):
    """Handles view and submission for registration page 1: profile request

    If the user is not authenticated, this function displays the profile request form, else, it redirects to the data request form.

    URL:
        url(r'^register/profile_request/$', 'profile_request_view', name='profile_request_form'),

    Function:
        send_verification_email(): send verification email to ProfileRequest object

    Form:
        ProfileRequestForm in forms.py

    """
    ### Get session details
    profile_request_obj = request.session.get('profile_request_obj', None)
    data_request_session=request.session.get('data_request_session', None)

    ### Assign form
    form = ProfileRequestForm()
    ### Check if user is authenticated
    if request.user.is_authenticated():
        return HttpResponseRedirect(
            reverse('datarequests:data_request_form')
        )
    else:
        ### Check if form is being submitted
        if request.method == 'POST':
            form = ProfileRequestForm(request.POST)
            if form.is_valid():
                ### Update if sessions for profile and data request objects exist
                if profile_request_obj and data_request_session:
                    profile_request_obj.first_name = form.cleaned_data['first_name']
                    profile_request_obj.middle_name = form.cleaned_data['middle_name']
                    profile_request_obj.last_name = form.cleaned_data['last_name']
                    profile_request_obj.organization = form.cleaned_data['organization']
                    profile_request_obj.org_type=form.cleaned_data['org_type'].val
                    profile_request_obj.contact_number = form.cleaned_data['contact_number']
                    ### If email is changed, send_verification_email to new email
                    if not profile_request_obj.email == form.cleaned_data['email']:
                        profile_request_obj.email = form.cleaned_data['email']
                        profile_request_obj.send_verification_email()
                    profile_request_obj.save()
                ### Save if no session yet
                else:
                    profile_request_obj = form.save()
                    profile_request_obj.status = "unconfirmed"
                    profile_request_obj.save()
                    profile_request_obj.send_verification_email()
                ### Add obj to session
                request.session['profile_request_obj']= profile_request_obj
                request.session.set_expiry(900)
                ### Redirect to 2nd page of registration
                return HttpResponseRedirect(
                    reverse('datarequests:data_request_form')
                )
        elif request.method == 'GET':
            ### If the user pressed back
            if data_request_session and profile_request_obj:
                initial = {
                    'first_name': profile_request_obj.first_name,
                    'middle_name': profile_request_obj.middle_name,
                    'last_name': profile_request_obj.last_name,
                    'organization': profile_request_obj.organization,
                    'org_type': profile_request_obj.org_type,
                    'organization_other': profile_request_obj.organization_other,
                    'email': profile_request_obj.email,
                    'contact_number': profile_request_obj.contact_number,
                    'location': profile_request_obj.location
                }
                form = ProfileRequestForm(initial = initial)
        ### Form is not submitted, therefore show blank form
        return render(
            request,
            'datarequests/registration/profile.html',
            {'form': form}
        )

def data_request_view(request):
    """Handles view and submission for registration page 2: data request

    This function displays the data request form. Upon successful submission of this form; if the user is logged in, it redirects to the home page, else, this function redirects the user to the notice of email verification.

    If the data request has a shapefile, it triggers the place_name_update, compute_size_update, and tag_request_suc tasks in the background.

    This function handles the shapefile separately. It is handled through DataRequestShapefileForm, while the other data is handled by DataRequestForm.

    This function handles the document separately. It is handled through the create_letter_document function, which creates a Document object to be tagged to the profile, if it exists, else to the profile_request.

    URL:
        url(r'^register/data_request/$', 'data_request_view', name='data_request_form'),

    Function:
        create_letter_document(request_letter, profile=None, profile_request=None)

    Form:
        DataRequestForm in forms.py

    """
    ### Get session details
    profile_request_obj = request.session.get('profile_request_obj', None)

    if not profile_request_obj:#for users logged in
        pprint("no profile request object found")
    ### If user is not logged in, did not submit `profile_request_form`, or had the session expire (time set in profile_request_view's request.session.set_expiry(900))
    if not request.user.is_authenticated() and not profile_request_obj:
        return redirect(reverse('datarequests:profile_request_form'))

    request.session['data_request_session'] = True

    form = DataRequestForm()
    ### Check if form is being submitted
    if request.method == 'POST' :
        pprint("detected data request post")

        ### set post_data for the use of DataRequestShapefileForm
        post_data = request.POST.copy()
        post_data['permissions'] = '{"users":{"dataRegistrationUploader": ["view_resourcebase"] }}'

        ### Handle formatting of data_class (DEM, ORTHO, etc)
        data_classes = post_data.getlist('data_class_requested')
        data_class_objs = []
        pprint(data_classes)
        pprint("len:"+str(len(data_classes)))
        if len(data_classes) == 1: #format when only one data class is selected
            post_data.setlist('data_class_requested',data_classes[0].replace('[','').replace(']','').replace('"','').split(','))
            pprint(post_data.getlist('data_class_requested'))

        ### Assign form
        details_form = DataRequestForm(post_data, request.FILES)
        data_request_obj = None
        errormsgs = []
        out = {}
        out['errors'] = {}
        out['success'] = False
        saved_layer = None
        ### Check if form is valid
        if not details_form.is_valid(): # with errors
            ### Handle errors
            for e in details_form.errors.values():
                errormsgs.extend([escape(v) for v in e])
            out['errors'] =  dict(
                (k, map(unicode, v))
                for (k,v) in details_form.errors.iteritems())
            pprint(out['errors'])
        else: # no errors
            tempdir = None
            shapefile_form = DataRequestShapefileForm(post_data, request.FILES)
            if u'base_file' in request.FILES:
                if shapefile_form.is_valid():
                    title = shapefile_form.cleaned_data["layer_title"]
                    # Replace dots in filename - GeoServer REST API upload bug
                    # and avoid any other invalid characters.
                    # Use the title if possible, otherwise default to the filename
                    if title is not None and len(title) > 0:
                        name_base = title
                    else:
                        name_base, __ = os.path.splitext(
                            shapefile_form.cleaned_data["base_file"].name)

                    name = slugify(name_base.replace(".", "_"))

                    try:
                        # Moved this inside the try/except block because it can raise
                        # exceptions when unicode characters are present.
                        # This should be followed up in upstream Django.
                        tempdir, base_file = shapefile_form.write_files()
                        registration_uploader, created = Profile.objects.get_or_create(username='dataRegistrationUploader')
                        pprint("saving jurisdiction")
                        saved_layer = file_upload(
                            base_file,
                            name=name,
                            user=registration_uploader,
                            overwrite=False,
                            charset=shapefile_form.cleaned_data["charset"],
                            abstract=shapefile_form.cleaned_data["abstract"],
                            title=shapefile_form.cleaned_data["layer_title"],
                        )
                    except Exception as e:
                        exception_type, error, tb = sys.exc_info()
                        print traceback.format_exc()
                        out['success'] = False
                        out['errors'] = "An unexpected error was encountered. Check the files you have uploaded, clear your selected files, and try again."
                        # Assign the error message to the latest UploadSession of the data request uploader user.
                        latest_uploads = UploadSession.objects.filter(
                            user=registration_uploader
                        ).order_by('-date')
                        if latest_uploads.count() > 0:
                            upload_session = latest_uploads[0]
                            upload_session.error = str(error)
                            upload_session.traceback = traceback.format_exc(tb)
                            upload_session.context = "Data requester's jurisdiction file upload"
                            upload_session.save()
                            out['traceback'] = upload_session.traceback
                            out['context'] = upload_session.context
                            out['upload_session'] = upload_session.id
                    else: # No exceptions
                        pprint("layer_upload is successful")
                        out['success'] = True
                        out['url'] = reverse(
                            'layer_detail', args=[
                                saved_layer.service_typename])

                        upload_session = saved_layer.upload_session
                        upload_session.processed = True
                        upload_session.save()
                        permissions = {
                            'users': {'dataRegistrationUploader': []},
                            'groups': {}
                        }
                        if request.user.is_authenticated():
                            permissions = {
                                'users': {request.user.username : ['view_resourcebase']},
                                'groups': {}
                            }

                        if permissions is not None and len(permissions.keys()) > 0:
                            saved_layer.set_permissions(permissions)

                        jurisdiction_style.delay(saved_layer)
                    finally:
                        if tempdir is not None:
                            shutil.rmtree(tempdir)
                else: # If DataRequestShapefileForm has errors
                    for e in shapefile_form.errors.values():
                        errormsgs.extend([escape(v) for v in e])
                    out['success'] = False
                    out['errors'].update(dict(
                            (k, map(unicode, v))
                            for (k,v) in shapefile_form.errors.iteritems()
                    ))
                    pprint(out['errors'])
                    out['errormsgs'] = out['errors']
        ### Handling of errors
        if not out['errors']:
            out['success'] = True
            data_request_obj = details_form.save()
            ### Trigger create_letter_document function which creates the document object and tags it to profile or profile_request
            ### Authenticated users: tag profile account and reset the status to "pending"
            if request.user.is_authenticated() and not request.user.username  == 'AnonymousUser':
                request_letter = create_letter_document(details_form.clean()['letter_file'], profile = request.user)
                data_request_obj.request_letter = request_letter
                data_request_obj.save()
                data_request_obj.profile = request.user
                data_request_obj.save()
                data_request_obj.set_status("pending")
            ### Unauthenticated users: tag profile_request to data_request and vice versa, status does not need to change
            else:
                request_letter = create_letter_document(details_form.clean()['letter_file'], profile_request = profile_request_obj)
                data_request_obj.request_letter = request_letter
                data_request_obj.save()
                data_request_obj.profile_request = profile_request_obj
                data_request_obj.save()
                profile_request_obj.data_request= data_request_obj
                profile_request_obj.save()
            data_request_obj.save()
            ### If there is a uploaded shapefile, trigger the following tasks: place_name_update, compute_size_update, and tag_request_suc
            if saved_layer:
                data_request_obj.jurisdiction_shapefile = saved_layer
                data_request_obj.save()
                place_name_update.delay([data_request_obj])
                compute_size_update.delay([data_request_obj])
                tag_request_suc.delay([data_request_obj])
            status_code = 200
            pprint("data request has been succesfully submitted")
            ### If the user is not logged in, this function redirects the user to the notice of email verification, else if user is logged in, it redirects to the home page.
            if profile_request_obj and not request.user.is_authenticated():
                out['success_url'] = reverse('datarequests:email_verification_send')
                out['redirect_to'] = reverse('datarequests:email_verification_send')
            elif request.user.is_authenticated():
                messages.info(request, "Your request has been submitted")
                out['success_url'] = reverse('home')
                out['redirect_to'] = reverse('home')
            ### Delete sessions
            del request.session['data_request_session']
            if 'profile_request_obj' in request.session:
                del request.session['profile_request_obj']
        else:
            status_code = 400
            pprint("data request post status_code 400")
        return HttpResponse(
            json.dumps(out),
            mimetype='application/json',
            status=status_code)
    return render(
        request,
        'datarequests/registration/shapefile.html',
        {
            'charsets': CHARSETS,
            'is_layer': True,
            'form': form,
            'support_email': settings.LIPAD_SUPPORT_MAIL,
        })

def email_verification_send(request):
    """Page that displays a notice about the verification email.

    If the user is not authenticated, this function/page displays a notice about the verification email, else, it redirects home.

    URL:
        url(r'^register/verification-sent/$', 'email_verification_send', name='email_verification_send'),

    """

    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('home'))

    context = {
        'support_email': settings.LIPAD_SUPPORT_MAIL,
    }
    return render(
        request,
        'datarequests/registration/verification_sent.html',
        context
    )

def email_verification_confirm(request):
    """Page that displays a notice for confirmed email addresses.

    This function is triggered via the link provided through email to the user upon submitting of registration for email verification.
    This function changes the status of the user from "unconfirmed" to "pending"
    If the key and email from the url matches an object in ProfileRequest, this will display verification_done.html, else, this will display verification_failed.html

    URL:
        url(r'^register/email-verified/$', 'email_verification_confirm', name='email_verification_confirm'),

    """
    key = request.GET.get('key', None)
    email = request.GET.get('email', None)

    context = {
        'support_email': settings.LIPAD_SUPPORT_MAIL,
    }

    if key and email:
        profile_request = None
        try:
            profile_request = ProfileRequest.objects.get(
                email=email,
                verification_key=key,
            )
            pprint(profile_request.status)
            # Only verify once
            if profile_request.status == "unconfirmed":
                #profile_request.set_status("pending")
                profile_request.status = "pending"
                profile_request.verification_date = timezone.now()
                pprint(email+" "+profile_request.status)
                profile_request.save()
                pprint(email+" "+profile_request.status)
                profile_request.send_new_request_notif_to_admins()
                profile_requests = ProfileRequest.objects.filter(email=email, status="unconfirmed")
                set_status_for_multiple_requests.delay(profile_requests,"cancelled")


        except ObjectDoesNotExist:
            profile_request = None

        if profile_request:
            return render(
                request,
                'datarequests/registration/verification_done.html',
                context
            )

    return render(
        request,
        'datarequests/registration/verification_failed.html',
        context
    )

def create_letter_document(request_letter, profile=None, profile_request=None):
    """Creates document object

    This is a utility function used to create the Document object to be saved in the database should a user decide to include a request letter in his/her data request.
    The request letter is mapped to a profile or a profile request. If both are absent, PermissionDenied is raised.

    """
    if not profile and not profile_request:
        raise PermissionDenied

    details = None
    letter_owner = None
    permissions = None

    if profile:
        pprint("profile is not empty")
        details = profile
        letter_owner = profile
        permissions = {"users":{profile.username:["view_resourcebase","download_resourcebase"]}}
    else:
        pprint("profile request is not empty")
        details = profile_request
        letter_owner, created = Profile.objects.get_or_create(username='dataRegistrationUploader')
        permissions = {"users":{"dataRegistrationUploader":["view_resourcebase"]}}

    requester_name = unidecode(details.first_name+" " +details.last_name)
    letter = Document()
    letter.owner = letter_owner
    letter.doc_file = request_letter
    letter.title = requester_name + " Request Letter " +datetime.datetime.now().strftime("%Y-%m-%d")
    letter.is_published = False
    letter.save()
    letter.set_permissions(permissions)

    return letter
