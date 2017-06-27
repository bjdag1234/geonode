from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse_lazy
from pprint import pprint
from geonode.base.enumerations import CHARSETS
from django.utils.encoding import smart_str
from .forms import MetaDataJobForm
from .models import AutomationJob
# Create your views here.


def create_obj():
    pass


@login_required
@user_passes_test(lambda u: u.is_superuser)
def metadata_job(request):
    print 'METHOD IS ', request.method
    if request.method == 'POST':
        print 'Method: ', str(request.method)
        form = MetaDataJobForm(request.POST)
        if form.is_valid():
            print 'Valid'
            print 'Input Directory', smart_str(form.cleaned_data['input_dir'])
            print 'Processor', smart_str(form.cleaned_data['processor'])
            print 'Datatype', smart_str(form.cleaned_data['datatype'])
            # print request
            # output_dir, date_submitted, status, log,
            print 'Saving...'
            form.save()
            return render(request, "update_task.html")

    else:
        # for any other method, create a blank form
        print 'Method:', str(request.method)
        form = MetaDataJobForm()

    return render(request, 'input_job.html', {'input_job_form': form})

def dem_metadata_job(request):
    print 'METHOD IS ', request.method
    if request.method == 'POST':
        print 'Method: ', str(request.method)
        form = MetaDataJobForm(request.POST)
        if form.is_valid():
            print 'Valid'
            print 'Input Directory', smart_str(form.cleaned_data['input_dir'])
            print 'Processor', smart_str(form.cleaned_data['processor'])
            print 'Datatype', smart_str(form.cleaned_data['datatype'])
            # print request
            # output_dir, date_submitted, status, log,
            print 'Saving...'
            form.save()
            return render(request, "update_task.html")

    else:
        # for any other method, create a blank form
        print 'Method:', str(request.method)
        form = MetaDataJobForm()

    return render(request, 'dem_job.html', {'dem_job_form': form})
