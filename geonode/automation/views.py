from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

# Create your views here.

def create_obj():
    pass

def trigger_input(request):
    print 'REQUEST POST IS', request.POST
    print 'SSSSSSSSSSOMETHING'
    # sample = {'datatype': 'something'}
    params = {}
    # sample data
    folder_list = ['DTM_1','DTM_2']
    input_datatype = request.POST['datatype']
    turnover_id = 'TOID1'


    return sample
