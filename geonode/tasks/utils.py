import geonode.settings as settings
import logging
from celery.utils.log import get_task_logger
from geonode.layers.models import Layer
from geonode.cephgeo.models import RIDF
import psycopg2
import psycopg2.extras

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


def check_keyword(mode, results, layer, rb_field):

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
            if rb_field in r:
                temp_fp = check_floodplain_names(r[rb_field])
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


def form_query_rb(layer_name, params):
    fhm_coverage = params.get('fhm_coverage')
    rb_field = params.get('rb_field')
    query = '''
WITH l AS (
    SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
    FROM ''' + layer_name + ''' AS f
)'''

    # WITH l AS (
    #     SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
    #     FROM <layer_name> AS f
    # )
    # SELECT d."RBFP_name",
    # (ST_AREA(ST_INTERSECTION(d.the_geom, l.the_geom))/ST_AREA(d.the_geom)) as proportion
    # FROM FHM_COVERAGE AS d, l
    # WHERE ST_INTERSECTS(d.the_geom, l.the_geom)
    # ORDER BY proportion desc, d."RBFP_name"
    query += '''
SELECT d."''' + rb_field + '''",
(ST_AREA(ST_INTERSECTION(d.the_geom, l.the_geom))/ST_AREA(d.the_geom)) as proportion
FROM ''' + fhm_coverage + ''' AS d, l
WHERE ST_INTERSECTS(d.the_geom, l.the_geom)
ORDER BY proportion desc, d."''' + rb_field + '''"'''

    print query
    return query


def form_query(layer_name, mode, params):

    query = '''
WITH l AS (
    SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
    FROM ''' + layer_name + ''' AS f
)'''

    # intersecting sar with delineation
    if mode == 'sar' or mode == 'fhm_2':
        # WITH l AS (
        #     SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
        #     FROM <layer_name> AS f
        # )
        # SELECT DISTINCT d."SUC" FROM <PL1_SUC_MUNIS> AS d, l
        # WHERE ST_Intersects(d.the_geom, l.the_geom)
        deln = params.get('suc_municipality_layer')
        query += '''
SELECT DISTINCT d."SUC" FROM ''' + deln + ''' AS d, l'''

    # intersect muni of fhm to fhm_coverage
    elif mode == 'fhm':
        # WITH l AS (
        #     SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
        #     FROM <layer_name> AS f
        # )
        # SELECT d."RBFP_name", d."SUC" FROM FHM_COVERAGE AS d, l
        # WHERE ST_Intersects(d.the_geom, l.the_geom)
        deln = params.get('fhm_coverage')
        rb_field = params.get('rb_field')
        query += '''
SELECT d."''' + rb_field + '''", d."SUC" FROM ''' + deln + ''' AS d, l'''

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


def rb_title(layer, params):
    # Disabled intersection of RB FHM due to Datastore DB processing failure
    # conn = psycopg2.connect(("host={0} dbname={1} user={2} password={3}".format
    #                          (settings.DATABASE_HOST,
    #                           settings.DATASTORE_DB,
    #                           settings.DATABASE_USER,
    #                           settings.DATABASE_PASSWORD)))
    # cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # query_int = form_query_rb(layer.name, params)
    # results = execute_query(query_int, layer, cur, conn)

    # layer_title = '{0} {1} Year Flood Hazard Map'.format(
    #     str(results[0][0]), flood_year).replace("_", " ").title()

    print 'Get title from Layer name.'
    rb_name = layer.name.split('_fh')[0]
    flood_year = int(layer.name.split('fh')[1].split('yr')[0])
    print layer.name, ': flood_year:', flood_year
    layer_title = ''
    layer_title = '{0} {1} Year Flood Hazard Map'.format(
        rb_name, flood_year).replace("_", " ").title()

    if layer.title != layer_title:
        print layer.name, ': Setting layer.title...'
        layer.title = layer_title

    layer.save()

    # conn.close()
    return layer


def muni_title(layer):
    layer_title = ''
    flood_year = int(layer.name.split('fh')[1].split('yr')[0])
    print layer.name, ': flood_year:', flood_year
    # Get muni code
    muni_code = layer.name.split('_fh')[0]
    print layer.name, ': muni_code:', muni_code

    # Get ridf
    ridf_obj = RIDF.objects.get(muni_code__icontains=muni_code)
    ridf = eval('ridf_obj._' + str(flood_year) + 'yr')
    print layer.name, ': ridf: ', ridf

    muni = ridf_obj.muni_name
    prov = ridf_obj.prov_name

    layer_title = '{0}, {1} {2} Year Flood Hazard Map'.format(
        muni, prov, flood_year).replace("_", " ").title()
    if ridf_obj.iscity:
        layer_title = 'City of ' + layer_title
    print layer.name, ': layer_title:', layer_title

    if layer.title != layer_title:
        print layer.name, ': Setting layer.title...'
        layer.title = layer_title

    return layer


def update_title(layer, params):
    title_option = params.get('title')

    title_option = str(title_option)
    if 'rb' in title_option:
        layer = rb_title(layer, params)
    else:
        layer = muni_title(layer)
