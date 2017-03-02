from geonode.settings import GEONODE_APPS
import geonode.settings as settings
import os
from geonode.layers.models import Layer
from pprint import pprint
import csv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geonode.settings")

def list_layer_names():
    layers = Layer.objects.all().values_list('name', flat=True)
    return layers

def crosscheck_fhm(csv_file):
    # get layers names in geonode DB
    layers = list_layer_names()
    crosscheck_list = {} 

    # check for file existence
    if not os.path.isfile(csv_file):
        print '{0} file not found'.format(msg)
    else:
        with open(csv_file) as csv_file:
            first_line = True
            field_names = ['layer_name','owner/uploader']
            reader = csv.DictReader(csv_file, fieldnames = field_names)
            for row in reader:
                if first_line:
                    first_line = False
                    continue
                print row['layer_name']
                if row['layer_name'] not in layers:
                    crosscheck_list[row['layer_name']] = row['owner/uploader']
                #     print 'Yes'
                # else:
                #     print 'No'

    # if there are items not in database of lipad-fmc write on file
    # double check these layers
    if crosscheck_list is not None:
        with open('fhm_not_in_fmc.csv','w') as write_file:                        
            field_names  = ['layer_name','owner/uploader']
            writer = csv.DictWriter(write_file,fieldnames = field_names)
            # writer.writeheader()
            for key in sorted(crosscheck_list):
                writer.writerow({'layer_name': key, 'owner/uploader' : crosscheck_list[key]})



if __name__ == '__main__':
    csv_file = 'fhm_list_production.csv'
    crosscheck_fhm(csv_file)
    print 'Done'