from django.db import models
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.mail import EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils import dateformat
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _
from django.utils.encoding import iri_to_uri
from django.utils.http import urlquote
from django_enumfield import enum
from django.core import validators
from django_auth_ldap.backend import LDAPBackend, ldap_error

from model_utils import Choices
from model_utils.models import TimeStampedModel, StatusModel

from geonode.cephgeo.models import UserJurisdiction
from geonode.datarequests.utils import create_login_credentials, create_ad_account, add_to_ad_group
from geonode.documents.models import Document
from geonode.layers.models import Layer
from geonode.people.models import OrganizationType, Profile

from pprint import pprint
from unidecode import unidecode

import traceback

from django.conf import settings as local_settings


class LipadOrgType(models.Model):
    """Lists all the Organization Type used in Profile Requests

    This model lists all the organization type used in the Profile Request.
    Fields:
        val - the acronym used for the oranization type
        display_val - the complete name of the organization type as displayed in the forms
        category - the merged version of the organization types. Used in distribution status

    """
    val = models.CharField(_('Value'), max_length=100)
    display_val = models.CharField(_('Display'), max_length=100)
    category = models.CharField(_('Sub'), max_length=100, null=True)

    class Meta:
        app_label = "datarequests"

    def __unicode__(self):
        return (_('{}').format(self.val,))

class BaseRequest(TimeStampedModel):
    """Both Profile and Data Requests share

    The base request model is an abstract class from which the profile and data requests inherit. It inherits from the TimeStampedModel class which automatically gives it the created and modified fields.
    Fields:
        profile - a mapping to a user Profile object
        administrator - a mapping to a superuser Profile object. Set to the admin Profile object who made the last modifications via editing or status changes done through the website
        rejection_reason - a container for saving the cause of rejection
        additional_remarks - a container for possible additional comments by an administrator
        additional_rejection_reason - a more elaborate version of the rejection_reason

    """

    STATUS = Choices(
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('cancelled', _('Cancelled')),
        ('rejected', _('Rejected')),
        ('unconfirmed',_('Unconfirmed Email')),
    )

    profile = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    administrator = models.ForeignKey(
        Profile,
        null=True,
        blank=True,
        related_name="admin+"
    )

    rejection_reason = models.CharField(
        _('Reason for Rejection'),
        blank=True,
        null=True,
        max_length=100,
    )

    additional_remarks = models.TextField(
        blank = True,
        null = True,
        help_text= _('Additional remarks by an administrator'),
    )

    additional_rejection_reason = models.TextField(
        _('Additional details about rejection'),
        blank=True,
        null=True,
        )

    class Meta:
        abstract = True
        app_label = "datarequests"

class RequestRejectionReason(models.Model):
    """Rejection Reason model

    This is where the reason for rejection is stored.

    """
    reason = models.CharField(_('Reason for rejection'), max_length=100)

    class Meta:
        app_label = "datarequests"

    def __unicode__(self):
        return (_('{}').format(self.reason,))
