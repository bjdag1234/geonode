from django.db import models
from datetime import datetime
# Create your models here.


class AutomationJob(models.Model):
    datatype = models.CharField(max_length=10, blank=False, null=False)
    pathname = models.CharField(max_length=100, blank=False, null=False)
    date_submitted = models.DateTimeField(
        default=datetime.now, blank=False, null=False)
    status = models.CharField(max_length=50, blank=False, null=False)
    turnover_id = models.CharField(max_length=10, blank=False, null=False)
    log = models.TextField(null=False,blank=True)

    def __unicode__(self):
        return "{0} {1} {2} {3}". \
            format(self.datatype, self.pathname,
                   self.date_submitted, self.status)
