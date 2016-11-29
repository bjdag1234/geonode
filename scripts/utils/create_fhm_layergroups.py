#!/usr/bin/env python

from __future__ import print_function
from geonode.settings import GEONODE_APPS
import geonode.settings as settings
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'geonode.settings')

from geoserver.catalog import Catalog


cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
              username=settings.OGC_SERVER['default']['USER'],
              password=settings.OGC_SERVER['default']['PASSWORD'])

error_layers = open('error_layers.log', 'w')

for yr in ['5', '25', '100']:

    print('FHM ' + yr + 'yr...')

    # Get list of layers
    print('Getting list of layers...', end='')
    layers = []
    styles = []
    for layer in cat.get_layers():
        try:
            if ('fh' + yr + 'yr' in layer.name and
                    layer.resource.enabled == 'true'):
                # print(layer.name)
                layers.append(layer.name)
                if 'Merge' in layer.resource.attributes:
                    styles.append('fhm_merge')
                else:
                    styles.append('fhm')
        except:
            print('Error fetching layer:', layer.name)
            print(layer.name, file=error_layers)
    print('Done!')

    lg_name = 'fhms_' + yr + 'yr'
    print('lg_name:', lg_name)

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
    lg = cat.create_layergroup(
        lg_name, layers=layers, styles=styles, workspace='geonode')
    cat.save(lg)
    cat.reload()
    print('Done!')

    # break

error_layers.close()
