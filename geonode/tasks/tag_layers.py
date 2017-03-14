import geonode.settings as settings
from celery.utils.log import get_task_logger
from geonode.layers.models import Layer
import logging
import psycopg2
import psycopg2.extras

logger = get_task_logger("geonode.tasks.update")
logger.setLevel(logging.INFO)


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


def assign_tags(mode, results, layer):

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
                if len(keywords) == 0 or r['rb_name'] not in keywords:
                    logger.info('%s: %s: Adding keyword: %s',
                                layer.name, mode, r['rb_name'])
                    layer.keywords.add(r['rb_name'])
                    has_changes = True
                if len(fp_tags) == 0 or r['rb_name'] not in fp_tags:
                    logger.info('%s: %s: Adding FP tag: %s',
                                layer.name, mode, r['rb_name'])
                    layer.floodplain_tag.add(r['rb_name'])
                    has_changes = True
            if 'SUC' in r:
                if len(keywords) == 0 or r['SUC'] not in keywords:
                    logger.info('%s: %s: Adding keyword: %s', layer.name, mode,
                                r['SUC'])
                    layer.keywords.add(r['SUC'])
                    has_changes = True
                if len(suc_tags) == 0 or r['SUC'] not in suc_tags:
                    logger.info('%s: %s: Adding SUC tag: %s', layer.name, mode,
                                r['SUC'])
                    layer.SUC_tag.add(r['SUC'])
                    has_changes = True
        elif mode == 'fhm':
            # Floodplain - SUC
            if 'Floodplain' in r:
                temp_fp = check_floodplain_names(r['Floodplain'])
                print 'TEMP FP is: ', temp_fp
                for t in temp_fp:
                    if len(keywords) == 0 or t not in keywords:
                        logger.info('%s: %s: Adding keyword: %s',
                                    layer.name, mode, t)
                        layer.keywords.add(t)
                        has_changes = True
                    if len(fp_tags) == 0 or t not in fp_tags:
                        logger.info('%s: %s: Adding FP tag: %s',
                                    layer.name, mode, t)
                        layer.floodplain_tag.add(t)
                        has_changes = True
            if 'SUC' in r:
                if len(keywords) == 0 or r['SUC'] not in keywords:
                    logger.info('%s: %s: Adding keyword: %s', layer.name, mode,
                                r['SUC'])
                    layer.keywords.add(r['SUC'])
                    has_changes = True
                if len(suc_tags) == 0 or r['SUC'] not in suc_tags:
                    logger.info('%s: %s: Adding SUC tag: %s', layer.name, mode,
                                r['SUC'])
                    layer.SUC_tag.add(r['SUC'])
                    has_changes = True
        elif mode == 'sar':
            # SUC
            if 'SUC' in r:
                if r['SUC'] == 'UPMin':
                    r['SUC'] = 'UPM'
                if len(keywords) == 0 or r['SUC'] not in keywords:
                    logger.info('%s: %s: Adding keyword: %s', layer.name, mode,
                                r['SUC'])
                    layer.keywords.add(r['SUC'])
                    has_changes = True
                if len(keywords) == 0 or r['SUC'] not in suc_tags:
                    logger.info('%s: %s: Adding SUC tag: %s', layer.name, mode,
                                r['SUC'])
                    layer.SUC_tag.add(r['SUC'])
                    has_changes = True

    logger.info('%s: Keywords: %s', layer.name, layer.keywords.names())
    logger.info('%s: Floodplain Tags: %s', layer.name,
                layer.floodplain_tag.names())
    logger.info('%s: SUC Tags: %s', layer.name, layer.SUC_tag.names())

    return has_changes


def fhm_suc(rb_name, cur, conn):
    # suc_result = None
    query = '''
select "SUC"
from ''' + settings.FHM_COVERAGE + '''
where "Floodplain"='%s' ''' % rb_name
    try:
        logger.info('select query: %s', query)
        cur.execute(query)
    except Exception:
        logger.exception('Error executing query!')
        conn.rollback()
    temp_result = cur.fetchone()
    if temp_result is not None:
        suc_result = temp_result[0]
        logger.info('SUC Result %s', suc_result)
        return suc_result
    else:
        print 'NO SUC for ', rb_name
        return []


def update_tags(layers, mode):
    # Connect to database
    conn = psycopg2.connect(("host={0} dbname={1} user={2} password={3}".format
                             (settings.DATABASE_HOST,
                              settings.DATASTORE_DB,
                              settings.DATABASE_USER,
                              settings.DATABASE_PASSWORD)))

    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    deln = ''
    # for mode, deln in [('dem', settings.RB_DELINEATION_DREAM),
    #                    ('sar', settings.PL1_SUC_MUNIS),
    #                    ('fhm', settings.FHM_COVERAGE)]:
    if mode == 'dem':
        results = {}
        for layer in layers:
            has_changes = False
            has_results = False
            hc = False
            rb_name = layer.name.split('_calibrated')[0].split('dem_')[
                1].replace('_', ' ')
            # if '/' in rb_name:
            #     temp = rb_name.split('/')
            #     for t in temp:
            #         results['rb_name'] = t
            #         assign_tags(keyword_filter, results, layer)
            if 'cdo iponan' in rb_name.lower():
                temp = ['Cagayan de Oro', 'Iponan']
                for t in temp:
                    suc_result = fhm_suc(t, cur, conn)
                    if len(suc_result) > 0:
                        results['SUC'] = suc_result
                    results['rb_name'] = t
                    print 'taglayer RESULTS ', results
                    hc = assign_tags(mode, [results], layer)
            elif 'ilog hilabangan' in rb_name.lower():
                results['rb_name'] = 'Ilog-Hilabangan'
                suc_result = fhm_suc(t, cur, conn)
                if len(suc_result) > 0:
                    results['SUC'] = suc_result
                print 'taglayer RESULTS ', results
                hc = assign_tags(mode, [results], layer)
            elif 'magasawang tubig' in rb_name.lower():
                results['rb_name'] = 'Mag-Asawang Tubig'
                suc_result = fhm_suc(t, cur, conn)
                if len(suc_result) > 0:
                    results['SUC'] = suc_result
                print 'taglayer RESULTS ', results
                hc = assign_tags(mode, [results], layer)
            else:
                results['rb_name'] = rb_name.title()
                suc_result = fhm_suc(results['rb_name'], cur, conn)
                if len(suc_result) > 0:
                    results['SUC'] = suc_result
                print 'taglayer RESULTS ', results
                hc = assign_tags(mode, [results], layer)

            if hc:
                try:
                    logger.info('%s: Saving layer...', layer.name)
                    layer.save()
                except Exception:
                    logger.exception('%s: ERROR SAVING LAYER', layer.name)
    # if sar or fhm
    else:
        for layer in layers:
            has_changes = False
            has_results = False
            hc = False
            logger.info('Layer name: %s', layer.name)

            # Construct query
            query = '''
    WITH l AS (
        SELECT ST_Multi(ST_Union(f.the_geom)) AS the_geom
        FROM ''' + layer.name + ''' AS f
    )'''

    #         if mode == 'dem':
    #             deln = settings.RB_DELINEATION_DREAM
    #             query += '''
    # SELECT d.rb_name FROM ''' + deln + ''' AS d, l '''
            if mode == 'sar':
                deln = settings.PL1_SUC_MUNIS
                query += '''
    SELECT DISTINCT d."SUC" FROM ''' + deln + ''' AS d, l'''
            elif mode == 'fhm':
                deln = settings.FHM_COVERAGE
                query += '''
    SELECT d."Floodplain", d."SUC" FROM ''' + deln + ''' AS d, l'''
    #         query += '''
    # FROM ''' + deln + ''' AS d, l'''

            logger.info('%s: mode: %s deln: %s', layer.name, mode, deln)
            # Get intersect
            query_int = (query + '''
     WHERE ST_Intersects(d.the_geom, l.the_geom);''')

            # Execute query
            try:
                logger.info('%s query_int: %s', layer.name, query_int)
                cur.execute(query_int)
            except Exception:
                logger.exception('%s: Error executing query_int!', layer.name)
                conn.rollback()
                # Skip layer
                continue

            # Get all results
            results = cur.fetchall()
            logger.info('%s: results: %s', layer.name, results)

            # Get no. of results
            if len(results) >= 1:
                has_results = True
                if mode == 'sar':
                    # tag SAR DEMs
                    rem_extents = layer.name.split('_extents')[0]
                    sar_layer = Layer.objects.get(name=rem_extents)
                    if sar_layer is not None:
                        hc = assign_tags(mode, results, sar_layer)
                    else:
                        logger.info('DOES NOT EXIST %s', sar_layer.name)
                    # tag SAR extents
                    hc = assign_tags(mode, results, layer)
                else:
                    hc = assign_tags(mode, results, layer)
                # if hc:
                #     has_changes = True

            if not has_results:
                logger.info('NO INTERSECTION %s', layer.name)

            if hc:
                try:
                    logger.info('%s: Saving layer...', layer.name)
                    layer.save()
                except Exception:
                    logger.exception('%s: ERROR SAVING LAYER', layer.name)
