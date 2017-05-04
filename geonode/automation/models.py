from django.db import models
from datetime import datetime
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
# Create your models here.


class AutomationJob(models.Model):
    DATATYPE_CHOICES = Choices(
        ('LAZ', _('LAZ')),
        ('Ortho', _('ORTHO')),
        ('DTM', _('DTM')),
        ('DSM', _('DSM'))
    )

    PROCESSOR_CHOICES = Choices(
        ('DRM', _('DREAM')),
        ('PL1', _('Phil-LiDAR 1')),
        ('PL2', _('Phil-LiDAR 2')),
    )

    STATUS_CHOICES = Choices(
        (0, 'pending', _('Pending Job')),
        (1, 'alpha_processing', _('Processing in Salad')),
        (2, 'beta_processing', _('Processing in Ceph')),
        (4, 'done', _('Uploaded in LiPAD')),
        # (-1, 'error', _('Error')),
    )

    datatype = models.CharField(
        choices=DATATYPE_CHOICES,
        max_length=10,
        help_text=_('Datatype of input'),
    )

    input_dir = models.CharField(
        _('Input Directory'),
        max_length=255,
        blank=False,
        null=False,
        help_text=_('Full path of directory location in server')
    )

    output_dir = models.CharField(
        _('Output Directory'),
        max_length=255,
        blank=False,
        null=False,
        help_text=_('Folder location in server')
    )

    processor = models.CharField(
        _('Data Processor'),
        choices=PROCESSOR_CHOICES,
        max_length=10,
    )

    date_submitted = models.DateTimeField(
        default=datetime.now,
        blank=False,
        null=False,
        help_text=_('The date which the job is submitted in LiPAD')
    )

    status = models.CharField(
        _('Job status'),
        choices=STATUS_CHOICES,
        default=STATUS_CHOICES.pending,
        max_length=10,
    )

    log = models.TextField(null=False, blank=True)

    def __unicode__(self):
        return "{0} {1} {2}". \
            format(self.datatype, self.date_submitted, self.status)
