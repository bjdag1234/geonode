#!/usr/bin/env python
from geonode.settings import GEONODE_APPS
import geonode.settings as settings

import os
import time
import subprocess
from os.path import dirname, abspath
import logging
from geonode.layers.models import Style
from geoserver.catalog import Catalog

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geonode.settings")

logger = logging.getLogger()
LOG_LEVEL = logging.INFO
FILE_LOG_LEVEL = logging.INFO
LOG_FOLDER = dirname(abspath(__file__)) + '/logs/'

# STYLE = 'test_sld.sld'


def setup_logging():

    # Setup logging
    logger.setLevel(LOG_LEVEL)
    formatter = logging.Formatter('[%(asctime)s] %(filename)s \
(%(levelname)s,%(lineno)d)\t: %(message)s')

    # Setup file logging
    filename = __file__.split('/')[-1]
    LOG_FILE_NAME = os.path.splitext(
        filename)[0] + '_' + time.strftime('%Y-%m-%d') + '.log'

    if not os.path.exists(LOG_FOLDER):
        os.makedirs(LOG_FOLDER)

    LOG_FILE = LOG_FOLDER + LOG_FILE_NAME
    fh = logging.FileHandler(LOG_FILE, mode='w')
    fh.setLevel(FILE_LOG_LEVEL)
    fh.setFormatter(formatter)
    logger.addHandler(fh)


def import_layers(path):
    # Execute importlayers

    IMPORTLAYERS_LOG_FILE_NAME = 'importlayers_' + \
        time.strftime('%Y-%m-%d') + '.log'

    IMPORTLAYERS_LOG_FILE = LOG_FOLDER + IMPORTLAYERS_LOG_FILE_NAME

    importlayers_cmd = 'python -u ../../manage.py importlayers -v 3 -u geoadmin' + ' '

    command = importlayers_cmd + path  # + log_cmd
    logger.info('Command: %s', command)

    command_list = command.split()
    logger.info('Command list: %s', command_list)

    text = ''

    try:

        logger.info('Execute command ...')

        output = subprocess.Popen(command_list, stdout=subprocess.PIPE)
        output.wait()
        text = output.communicate()[0]

        logger.info('Finished. Below is output of importlayers ')
        logger.info(text)
        # print 'Finished. Below is output of Popen'
        # print text

    except Exception:

        print 'Exception occurred'
        logger.exception('Exception occurred')

    return text


def exists_in_geonode(style_name):
    try:
        style = Style.objects.get(name=style_name)
        logger.info('Style found in GeoNode.')
        return True
    except Exception:
        logger.exception('Style does not exist')
    return False


def exists_in_geoserver(style_name):

    cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
                  username=settings.OGC_SERVER['default']['USER'],
                  password=settings.OGC_SERVER['default']['PASSWORD'])
    style = cat.get_style(style_name)

    if s is not None:
        logger.info('Style found in GeoNode.')
        return True
    return False


def style_exists():

    if exists_in_geonode() and exists_in_geoserver():
        return True
    return False


def create_style(style):
    """Creates style in geonode and geoserver."""

    name = style.split('.sld')

    sld_url = (settings.OGC_SERVER['default'][
               'LOCATION'] + 'rest/styles/' + style).lower()

    #: Geoserver style object
    with open(style) as f:
        logger.info('Creating style in GeoServer... ')
        cat.create_style(name, f.read())

    #: Geonode style object
    try:
        created_style = cat.get_style(name)

        if created_style is not None:
            Style.objects.create(name=created_style.sld_name,
                                 sld_title=created_style.sld_title,
                                 sld_body=created_style.sld_body,
                                 sld_url=sld_url)
    except Exception:
        logger.exception('Error in creating Style!')
        return False

    return True


def parse_arguments():

    parser = argparse.ArgumentParser(description="""Stand alone script for migrating data. Does the following:
        1. Uploads layers from <path> via importlayers command.
        2. Checks if <style> exists in GeoNode and GeoServer. If not, this script creates the style object for GeoNode and GeoServer.
        3. Updates layer styles by applying <style>.""")

    parser.add_argument(
        '--path', help="""Complete directory path of dataset to be imported.
            e.g. /mnt/pl2-storage_pool/CoastMap/SUC_UPLOADS/UPLB/PALAWAN/""")
    parser.add_argument(
        '--style', help="""Full name of SLD to be used. Must be in the same folder as this script.
            e.g. coastmap.sld """)


if __name__ == '__main__':

    args = parse_arguments()
    path = args.path
    style = args.style

    setup_logging()
    logger.info('Importing Layers ... ')
    import_msg = import_layers(path)
    logger.info('Finished importing layers.')

    style_created = True

    if import_msg != '':
        if not style_exists(style):
            style_created = create_style(style)

        if style_created:
            update_layer_styles(style)

    logger.info('Finished script')
