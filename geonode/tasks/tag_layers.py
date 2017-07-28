import geonode.settings as settings
from celery.utils.log import get_task_logger
from geonode.layers.models import Layer
import logging
import psycopg2
import psycopg2.extras
from utils import fhm_suc, check_floodplain_names, assign_keyword, check_keyword, dem_rb_name
from utils import form_query, execute_query, dem_mode, sar_mode

logger = get_task_logger("geonode.tasks.update")
logger.setLevel(logging.INFO)


def update_tags(layer, mode):
    conn = psycopg2.connect(("host={0} dbname={1} user={2} password={3}".format
                             (settings.DATABASE_HOST,
                              settings.DATASTORE_DB,
                              settings.DATABASE_USER,
                              settings.DATABASE_PASSWORD)))
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    deln = ''
    has_changes = False
    has_results = False
    # has_changes = False

    if mode == 'dem':
        dem_mode(layer, cur, conn, mode)
    # if sar or fhm
    else:
        logger.info('Layer name: %s', layer.name)

        query_int = form_query(layer.name, mode)
        results = execute_query(query_int, layer, cur, conn)

        if results:
            hc1 = False
            if mode == 'sar':
                hc1 = sar_mode(layer, mode, results)
            hc2 = check_keyword(mode, results, layer)
            has_changes = has_changes or hc1 or hc2

            if has_changes:
                try:
                    logger.info('[Comment] %s: Saving layer...', layer.name)
                    # layer.save()
                except Exception:
                    logger.exception('%s: ERROR SAVING LAYER', layer.name)
        else:
            print 'INTERSECT TO MUNICIPAL BOUNDARY'
            query_int = form_query(layer.name, 'fhm_2')
            results = execute_query(query_int, layer, cur, conn)
            if not results:
                logger.info('NO INTERSECTION %s IN %s', layer.name, deln)
            else:
                has_changes = check_keyword(mode, results, layer)
                if has_changes:
                    try:
                        logger.info('[Comment] %s: Muni intersected. Saving layer...', layer.name)
                        # layer.save()
                    except Exception:
                        logger.exception('%s: ERROR SAVING LAYER', layer.name)
    conn.close()
