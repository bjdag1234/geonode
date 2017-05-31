import geonode.settings as settings
import logging
from celery.utils.log import get_task_logger
from geonode.layers.models import Layer

logger = get_task_logger("geonode.tasks.update")
logger.setLevel(logging.INFO)


def fhm_suc(rb_name, cur, conn):
    # suc_result = None
    query = '''
select "SUC"
from ''' + settings.FHM_COVERAGE + '''
where "RBFP_name"='%s' ''' % rb_name
    try:
        logger.debug('select query: %s', query)
        cur.execute(query)
    except Exception:
        logger.exception('Error executing query!')
        conn.rollback()
    temp_result = cur.fetchone()
    if temp_result is not None:
        suc_result = temp_result[0]
        logger.debug('SUC Result %s', suc_result)
        return suc_result
    else:
        # print 'NO SUC for ', rb_name
        return []


def check_floodplain_names(fp_name):
    # In FHM Coverage
    # ampersand for 2 floodplains
    fp_name = fp_name.replace('_', ' ')
    if '&' in fp_name:
        fp_name = fp_name.split(' & ')
    # remove underscores, replace with spaces
    else:
        fp_name = [fp_name]
    return fp_name


def assign_keyword(keywords, rb_name, layer):
    if len(keywords) == 0 or rb_name not in keywords:
        logger.info('[Comment] %s: Adding keyword: %s', layer.name, rb_name)
        # layer.keywords.add(rb_name)
        return True
    return False


def check_keyword(mode, results, layer):

    has_changes = False
    keywords = layer.keywords.names()
    fp_tags = layer.floodplain_tag.names()
    suc_tags = layer.SUC_tag.names()

    for r in results:
        # print 'RESULTS R ', r['rb_name']
        # print 'RESULTS SUC', r['SUC']

        if mode == 'dem':
            # Riverbasin
            if 'rb_name' in r:
                hc1 = assign_keyword(keywords, r['rb_name'], layer)
                hc2 = assign_keyword(fp_tags, r['rb_name'], layer)
                has_changes = has_changes or hc1 or hc2
            if 'SUC' in r:
                hc1 = assign_keyword(keywords, r['SUC'], layer)
                hc2 = assign_keyword(suc_tags, r['SUC'], layer)
                has_changes = has_changes or hc1 or hc2
        elif mode == 'fhm':
            # Floodplain - SUC
            if 'RBFP_name' in r:
                temp_fp = check_floodplain_names(r['RBFP_name'])
                # print 'TEMP FP is: ', temp_fp
                for t in temp_fp:
                    hc1 = assign_keyword(keywords, t, layer)
                    hc2 = assign_keyword(fp_tags, t, layer)
                    has_changes = has_changes or hc1 or hc2
        if 'SUC' in r:
            if r['SUC'] == 'UPMin':
                r['SUC'] = 'UPM'
            hc1 = assign_keyword(keywords, r['SUC'], layer)
            hc2 = assign_keyword(suc_tags, r['SUC'], layer)
            has_changes = has_changes or hc1 or hc2

    logger.debug('%s: Keywords: %s', layer.name, layer.keywords.names())
    logger.debug('%s: Floodplain Tags: %s', layer.name,
                layer.floodplain_tag.names())
    logger.debug('%s: SUC Tags: %s', layer.name, layer.SUC_tag.names())

    return has_changes


def dem_rb_name(t, cur, conn, results):
    suc_result = fhm_suc(t, cur, conn)
    if len(suc_result) > 0:
        results['SUC'] = suc_result
    results['rb_name'] = t
    # print 'taglayer RESULTS ', results


def form_query(layer_name, mode):
    query = '''
WITH l AS (
    SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
    FROM ''' + layer_name + ''' AS f
)'''

    if mode == 'sar' or mode == 'fhm_2':
        deln = settings.PL1_SUC_MUNIS
        query += '''
SELECT DISTINCT d."SUC" FROM ''' + deln + ''' AS d, l'''
    elif mode == 'fhm':
        deln = settings.FHM_COVERAGE
        query += '''
SELECT d."RBFP_name", d."SUC" FROM ''' + deln + ''' AS d, l'''

        query = (query + '''
WHERE ST_Intersects(d.the_geom, l.the_geom);''')

    return query


def execute_query(query_int, layer, cur, conn):
    try:
        logger.debug('%s query_int: %s', layer.name, query_int)
        cur.execute(query_int)
    except Exception:
        logger.exception('%s: Error executing query_int!', layer.name)
        conn.rollback()
        return None
    # Get all results
    results = cur.fetchall()
    # print 'RESULT LENGTH %d ', len(results)
    logger.info('%s: results: %s', layer.name, results)
    return results


def dem_mode(layer, cur, conn, mode):
    results = {}
    # for layer in layers:
    has_changes = False
    has_results = False
    hc = False
    rb_name = layer.name.split('_calibrated')[0].split('dem_')[
        1].replace('_', ' ')
    # if '/' in rb_name:
    #     temp = rb_name.split('/')
    #     for t in temp:
    #         results['rb_name'] = t
    #         assign_keywords(keyword_filter, results, layer)
    if 'cdo iponan' in rb_name.lower():
        temp = ['Cagayan de Oro', 'Iponan']
        for t in temp:
            dem_rb_name(t, cur, conn, results)
            hc = assign_keyword(mode, [results], layer)
    elif 'ilog hilabangan' in rb_name.lower():
        results['rb_name'] = 'Ilog-Hilabangan'
        dem_rb_name(results['rb_name'], cur, conn, results)
        hc = assign_keyword(mode, [results], layer)
    elif 'magasawang tubig' in rb_name.lower():
        results['rb_name'] = 'Mag-Asawang Tubig'
        dem_rb_name(results['rb_name'], cur, conn, results)
        hc = assign_keyword(mode, [results], layer)
    else:
        results['rb_name'] = rb_name.title()
        dem_rb_name(results['rb_name'], cur, conn, results)
        hc = assign_keyword(mode, [results], layer)

    if hc:
        try:
            logger.info('[Comment] %s: Saving layer...', layer.name)
            # layer.save()
        except Exception:
            logger.exception('%s: ERROR SAVING LAYER', layer.name)


def sar_mode(layer, mode, results):
    rem_extents = layer.name.split('_extents')[0]
    sar_layer = Layer.objects.get(name=rem_extents)
    if sar_layer:
        hc = assign_keyword(mode, results, sar_layer)
        return True
    else:
        logger.info('DOES NOT EXIST %s', sar_layer.name)
