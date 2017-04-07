#!/usr/bin/env python
from geonode.settings import GEONODE_APPS
import geonode.settings as settings

from geonode.geoserver.helpers import ogc_server_settings
from geonode.layers.models import Layer
from geonode.layers.models import Style
from geoserver.catalog import Catalog
import argparse
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geonode.settings")


def delete_(layer):
    cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
                  username=settings.OGC_SERVER['default']['USER'],
                  password=settings.OGC_SERVER['default']['PASSWORD'])

    # layers = Layer.objects.filter(name__icontains=keyword)
    print 'LAYER ', layer.name
    print '#' * 40
    'Deleting {0} ...'.format(layer.name)
    try:
        gs_style = cat.get_style(layer.name)
        print '[Geoserver] Deleting default style ...'
        cat.delete(gs_style)
    except Exception:
        print 'No geoserver style'
        pass
    try:
        gs_layer = cat.get_layer(layer.name)
        print '[Geoserver] Deleting Layer ...'
        cat.delete(gs_layer)
    except Exception:
        print 'No geoserver layer'
        pass
    try:
        def_style = Style.objects.get(name=layer.name)
        print '[Geonode] Deleting default style ...'
        def_style.delete()
    except Exception:
        print 'No geonode style'
        pass
    try:
        print '[Geonode] Deleting Layer ...'
        layer.delete()
    except Exception:
        'Cannot delete geonode layer {0}'.format(layer.name)
        pass
    # break
