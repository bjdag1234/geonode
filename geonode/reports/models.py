from django.db import models

# Create your models here.
from django.utils.translation import ugettext_lazy as _
from geonode.people.models import Profile
from datetime import datetime

class DownloadCount(models.Model):
    date = models.DateTimeField( default=datetime.now)
    category = models.CharField(_('Category'), max_length=100)
    chart_group = models.CharField(_('Chart Group'), max_length=100)
    download_type = models.CharField(_('Type'), max_length=100)
    count = models.IntegerField(_('Count'))

class SUCLuzViMin(models.Model):
    province =  models.CharField(_('Province'), max_length=100)
    suc = models.CharField(_('Suc'), max_length=100)
    luzvimin = models.CharField(_('LuzViMin'), max_length=100)

class DownloadTracker(models.Model):
    timestamp = models.DateTimeField(default=datetime.now)
    actor = models.ForeignKey(
        Profile
    )
    title = models.CharField(_('Title'), max_length=100)
    resource_type = models.CharField(_('Resource Type'), max_length=100)
    keywords = models.CharField(_('Keywords'), max_length=100)
