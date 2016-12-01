#!/usr/bin/env python

from __future__ import print_function
from geonode.settings import GEONODE_APPS
import geonode.settings as settings
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode.settings')

from geoserver.catalog import Catalog
import argparse
import copy
import requests

json_template = {
    'layerGroup': {
        'name': '',
        'title': '',
        'mode': 'SINGLE',
        'workspace': {
            'name': 'geonode'
        },
        'publishables': {
            'published': []
        },
        'styles': {
            'style': []
        }
    }
}

layer_json_template = {
    '@type': 'layer',
    # 'name': 'san_juan_fh5yr_10m',
    'name': '',
    # 'href': 'http:\/\/localhost\/geoserver\/rest\/layers\/san_juan_fh5yr_10m.json'
    'href': ''
}

fhm_style_json = {
    'name': 'fhm',
    'href': 'http:\/\/localhost\/geoserver\/rest\/styles\/fhm.json'
}

fhm_merge_style_json = {
    'name': 'fhm_merge',
    'href': 'http:\/\/localhost\/geoserver\/rest\/styles\/fhm_merge.json'
}

parser = argparse.ArgumentParser()
parser.add_argument('yr', choices=['5', '25', '100'])
args = parser.parse_args()

yr = args.yr

print('FHM ' + yr + 'yr...')

cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
              username=settings.OGC_SERVER['default']['USER'],
              password=settings.OGC_SERVER['default']['PASSWORD'])

json_data = copy.deepcopy(json_template)


with open('error_layers_' + yr + '.log', 'w') as error_layers:

    # Get list of layers
    print('Getting list of layers...', end='')
    # layers = []
    # styles = []
    for layer in cat.get_layers():
        try:
            if ('fh' + yr + 'yr' in layer.name and
                    layer.resource.enabled == 'true'):
                # print(layer.name)

                # layers.append(layer.name)

                lj = copy.deepcopy(layer_json_template)
                lj['name'] = layer.name
                lj['href'] = 'http:\/\/localhost\/geoserver\/rest\/layers\/' + \
                    layer.name + '.json'
                json_data['layerGroup']['publishables']['published'].append(lj)

                if 'Merge' in layer.resource.attributes:
                    # styles.append('fhm_merge')
                    json_data['layerGroup']['styles'][
                        'style'].append(fhm_merge_style_json)
                else:
                    # styles.append('fhm')
                    json_data['layerGroup']['styles'][
                        'style'].append(fhm_style_json)
        except:
            print('Error fetching layer:', layer.name)
            print(layer.name, file=error_layers)
    print('Done!')

lg_name = 'fhms_' + yr + 'yr'
print('lg_name:', lg_name)
json_data['layerGroup']['name'] = lg_name
json_data['layerGroup']['title'] = 'Flood Hazard Maps ' + yr + 'yr'

# Delete existing layer group if exists
try:
    lg = cat.get_layergroup(name=lg_name, workspace='geonode')
    if lg:
        print('Deleting existing layergroup...', end='')
        cat.delete(lg)
        cat.reload()
        print('Done!')
except Exception:
    pass

# Create new layer group
print('Creating layer group...', end='')
# lg = cat.create_layergroup(
#     lg_name, layers=layers, styles=styles, workspace='geonode')
# cat.save(lg)
# cat.reload()

lgs_url = 'http://localhost/geoserver/rest/workspaces/geonode/layergroups.json'
_auth = (settings.OGC_SERVER['default']['USER'],
         settings.OGC_SERVER['default']['PASSWORD'])
r = requests.post(lgs_url, auth=_auth, json=json_data)
if r.status_code != 201:
    print('Error creating layer group! Exiting.')
    print('r.status_code:', r.status_code)
    print('r.reason:', r.reason)
    print('r.text:', r.text)
    exit(1)
print('Done!')

# break
