from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse_lazy
from pprint import pprint
from geonode.base.enumerations import CHARSETS
from django.utils.encoding import smart_str
from .forms import *
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
        form = DemJobForm(request.POST)
        if form.is_valid():
            print 'Valid'
            # print request
            # output_dir, date_submitted, status, log,
            """
            fields = ['dem_name', 'lidar_blocks', 'input_dir', 'output_dir', 'datatype', 'processor', 'target_os']
            '{"blocks": [["Dumaguete_Blk53C", 0, 0, 60.48, -0.5941, 0.1095], ["Dumaguete_Blk53C_reflights", 0, 0, 0.214, -0.5941, 0.1095], ["Dumaguete_Blk53D_reflights", 0, 0, 0, -0.5941, 0.1095], ["Dumaguete_Blk53D_additional_reflights", 0, 0, -0.1969, -0.5941, 0.1095], ["Dumaguete_Blk53D_supplement_reflights", 0, 0, -0.10246, -0.5941, 0.1095]], 
            "dem_file_path": "/home/ken/Dump/DEM_Sipalay", 
            "dem_name": "Sipalay"}'

            """
            print 'Saving...'
            dem_input_dict = {'dem_name': smart_str(form.cleaned_data['dem_name']),
                              'dem_file_path': smart_str(form.cleaned_data['input_dir']),
                              'blocks' : smart_str(form.cleaned_data['lidar_blocks']),
                                                         }
            
            dem_job = AutomationJob(datatype=smart_str(form.cleaned_data['datatype']),
                                    input_dir=str(dem_input_dict),
                                    output_dir=smart_str(form.cleaned_data['output_dir']),
                                    processor=smart_str(form.cleaned_data['processor']),
                                    target_os=smart_str(form.cleaned_data['target_os']),)
            dem_job.save()
            
            pprint(dem_job.__dict__)
            
            return render(request, "update_task.html")

    else:
        # for any other method, create a blank form
        print 'Method:', str(request.method)
        form = DemJobForm()

    return render(request, 'dem_job.html', {'dem_job_form': form})
