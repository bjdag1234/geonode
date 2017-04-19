#!/usr/bin/env python
from geonode.settings import GEONODE_APPS
import geonode.settings as settings

from geonode.geoserver.helpers import ogc_server_settings
from geonode.layers.models import Layer
from geonode.layers.models import Style
from geoserver.catalog import Catalog
import argparse
import os
import psycopg2

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geonode.settings")


def delete_layer(keyword, layer_list):
    # conn = psycopg2.connect(("host={0} dbname={1} user={2} password={3}".format
    #                          (settings.DATABASE_HOST, settings.DATASTORE_DB,
    #                           settings.DATABASE_USER, settings.DATABASE_PASSWORD)))
    # cur = conn.cursor()

    if layer_list is None:
        layers = ''
        layers = Layer.objects.filter(name__icontains=keyword)
    else:
        layers = []
        for l in layer_list:
            try:
                layers.append(Layer.objects.get(name=l))
            except:
                print 'NO LAYER ', l
    print 'LAYERS ', layers

    # cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
    #               username=settings.OGC_SERVER['default']['USER'],
    #               password=settings.OGC_SERVER['default']['PASSWORD'])

    total = len(layers)
    print 'TOTAL', total
    count = 1
    layername = ''
    for layer in layers:
        print 'LAYER ', layer.name
        layername = layer.name
        print '#' * 40
        # '[{0}/{1}] Deleting {2}'.format(count, total, layer.name)
        # try:
        #     gs_style = cat.get_style(layer.name)
        #     cat.delete(gs_style)
        # except Exception:
        #     print 'No geoserver style'
        #     pass
        # try:
        #     gs_layer = cat.get_layer(layer.name)
        #     cat.delete(gs_layer)
        # except Exception:
        #     print 'No geoserver layer'
        #     pass
        # try:
        #     def_style = Style.objects.get(name=layer.name)
        #     def_style.delete()
        # except Exception:
        #     print 'No geonode style'
        #     pass
        try:
            layer.delete()
        except Exception:
            print 'Cannot delete geonode layer'
            pass
    #     if layername != '':
    #         query = 'DROP TABLE IF EXISTS ' + layername + ' CASCADE;'
    #         print 'QUERY:', query
    #         try:
    #             cur.execute(query)
    #             conn.commit()
    #             print 'Deleted ' + layername + ' in pgsql database'
    #         except Exception:
    #             print layername + ' Not in pgsql database'
    #             conn.rollback()
    #     count += 1
    # cur.close()
    # conn.close()
    # break


def parse_arguments():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Enter keyword as layer name filter \
        eg _fh for FHM, sar_ for SAR, etc')
    parser.add_argument(
        'type', choices=['sar', 'dem', 'fhm', 'all'], action='append',
        help='Delete all layers in a specific layer type \
                        or delete all 3 layer type')
    parser.add_argument('--layer', nargs='+',
                        help='delete a specific layer or list of layers')
    args = parser.parse_args()
    return args

# if __name__ == '__main__':
args = parse_arguments()
for argType in args.type:
    if argType == 'fhm':
        keyword = '_fh'
        delete_layer(keyword, args.layer)
    elif argType == 'sar':
        keyword = 'sar_'
        delete_layer(keyword, args.layer)
    elif argType == 'dem':
        keyword = 'dem_'
        delete_layer(keyword, args.layer)
    else:
        print 'NO KEYWORD SUPPLIED. EXITING...'
