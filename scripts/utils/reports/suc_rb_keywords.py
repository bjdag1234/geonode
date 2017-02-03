#!/usr/bin/env python

# SUC, floodplain tagging for PL1 layers
# RB tagging for DREAM layers
from geonode.settings import GEONODE_APPS
import geonode.settings as settings
from geonode.layers.models import Layer
from osgeo import ogr
import logging
import multiprocessing
import os
import psycopg2
import sys


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geonode.settings")

_logger = logging.getLogger()
_LOG_LEVEL = logging.DEBUG
_CONS_LOG_LEVEL = logging.INFO
_FILE_LOG_LEVEL = logging.DEBUG

# source = ogr.Open(("PG:host={0} dbname={1} user={2} password={3}".format
#                    (settings.DATABASE_HOST, settings.DATASTORE_DB,
#                     settings.DATABASE_USER, settings.DATABASE_PASSWORD)))


def assign_tag(mode, records, layer):
    if mode == 'dream':
        _dict = {}
        _dict['floodplain'] = records[0][0]

        _logger.info('%s: FP: %s', layer.name, _dict['floodplain'])

        layer.keywords.add(_dict['floodplain'])
        layer.floodplain_tag.add(_dict['floodplain'])
        try:
            layer.save()

            _logger.debug('%s: Keywords: %s', layer.name,
                          layer.keywords.values_list())
            _logger.debug('%s: Floodplain Tag: %s', layer.name,
                          layer.floodplain_tag.values_list())

        except Exception:
            _logger.exception('%s: ERROR SAVING LAYER', layer.name)

    else:
        pair = {}
        pair['floodplain'] = records[0][0]
        pair['suc'] = records[0][1]

        _logger.info(
            '%s: FP:{0} - SUC:{1}', layer.name, pair['floodplain'], pair['suc'])

        layer.keywords.add(pair['floodplain'])
        layer.keywords.add(pair['suc'])
        layer.floodplain_tag.add(pair['floodplain'])
        layer.SUC_tag.add(pair['suc'])

        try:
            layer.save()

            _logger.debug('%s: Keywords: %s', layer.name,
                          layer.keywords.values_list())
            _logger.debug('%s: Floodplain Tag: %s', layer.name,
                          layer.floodplain_tag.values_list())
            _logger.debug('%s: SUC Tag: %s', layer.name,
                          layer.SUC_tag.values_list())

        except:
            _logger.exception('%s: ERROR SAVING LAYER', layer.name)


def tag_layers(layer):

    _logger.info('Layer name: %s', layer.name)

    conn = psycopg2.connect(("host={0} dbname={1} user={2} password={3}".format
                             (settings.DATABASE_HOST, settings.DATASTORE_DB,
                              settings.DATABASE_USER, settings.DATABASE_PASSWORD)))
    cur = conn.cursor()

    for m, d in [('dream', settings.RB_DELINEATION_DREAM),
                 ('', settings.FP_DELINEATION_PL1)]:

        _logger.info('%s: M: %s D: %s', layer.name, m, d)

        if m == 'dream':
            query = '''
                WITH fhm AS (
                    SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
                    FROM ''' + layer.name + ''' AS f
                )
                SELECT a.rb_name
                FROM ''' + d + ''' AS a, fhm
                WHERE ST_Contains(a.the_geom, ST_Centroid(fhm.the_geom))
                      AND ST_Intersects(a.the_geom, fhm.the_geom);
                '''
        else:
            query = '''
                WITH fhm AS (
                    SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
                    FROM ''' + layer.name + ''' AS f
                )
                SELECT a."FP_Name", a."SUC"
                FROM ''' + d + ''' AS a, fhm
                WHERE ST_Contains(a.the_geom, ST_Centroid(fhm.the_geom))
                      AND ST_Intersects(a.the_geom, fhm.the_geom);
                '''

        try:
            _logger.debug('%s query: %s', layer.name, query)
            cur.execute(query)

        except Exception:
            _logger.exception('%s: ERROR EXECUTING QUERY', layer.name)
            # traceback.print_exc()
            conn.rollback()
            continue

        records = cur.fetchall()
        _logger.info('%s: records: %s', layer.name, records)

        if len(records) > 1:
            if m == 'dream':
                _logger.error(
                    '%s: RETURNED MORE THAN 1 FP: %s', layer.name, records)
            else:
                _logger.error(
                    '%s: RETURNED MORE THAN 1 FP-SUC PAIR: %s', layer.name, records)

        elif len(records) == 1:
            assign_tag(m, records, layer)

        else:
            if m == 'dream':
                # layer_name = layer.name
                _logger.error('%s: RETURNED 0 FP: %s', layer.name, records)
            else:
                _logger.error('%s: RETURNED 0 FP-SUC PAIR: %s',
                              layer.name, records)


def _tag():
    # count = 1
    layers = Layer.objects.filter(name__icontains='_fh')
    pool.map_async(tag_layers, layers)
    pool.close()
    pool.join()


if __name__ == "__main__":

    _logger.setLevel(_LOG_LEVEL)
    formatter = logging.Formatter(
        '[%(asctime)s] (%(levelname)s) : %(message)s')

    # Setup console logging
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(_CONS_LOG_LEVEL)
    ch.setFormatter(formatter)
    _logger.addHandler(ch)

    # Setup file logging
    fh = logging.FileHandler(os.path.splitext(
        os.path.basename(__file__))[0] + '.log', mode='w')
    fh.setLevel(_FILE_LOG_LEVEL)
    fh.setFormatter(formatter)
    _logger.addHandler(fh)

    pool = multiprocessing.Pool()
    _tag()
