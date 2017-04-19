from geonode.settings import GEONODE_APPS
import geonode.settings as settings

from geonode.cephgeo.models import LidarCoverageBlock, CephDataObject

import os
from osgeo import ogr
import shapely
from shapely.wkb import loads
import math
import geonode.settings as settings
from collections import defaultdict
import json
from shapely.geometry import Polygon
# import datetime
from datetime import datetime, timedelta
from unidecode import unidecode
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geonode.settings")

# save Lidar coverage to model


def create_object(params):
    obj = LidarCoverageBlock.objects.create(uid=params['uid'],
                                            block_name=params['block_name'],
                                            adjusted_l=params['adjusted_l'],
                                            sensor=params['sensor'],
                                            processor=params['processor'],
                                            flight_num=params['flight_num'],
                                            mission_na=params['mission_na'],
                                            date_flown=params['date_flown'],
                                            x_shift_m=params['x_shift_m'],
                                            y_shift_m=params['y_shift_m'],
                                            z_shift_m=params['z_shift_m'],
                                            height_dif=params['height_dif'],
                                            rmse_val_m=params['rmse_val_m'],
                                            cal_ref_pt=params['cal_ref_pt'],
                                            val_ref_pt=params['val_ref_pt'],
                                            floodplain=params['floodplain'],
                                            pl1_suc=params['pl1_suc'],
                                            pl2_suc=params['pl2_suc'])
    return obj


def lidar_coverage_data():
    source = ogr.Open(("PG:host={0} dbname={1} user={2} password={3}".format(
        settings.DATABASE_HOST, settings.GIS_DATABASE_NAME, settings.DATABASE_USER, settings.DATABASE_PASSWORD)))

    layer = source.GetLayer(settings.LIDAR_COVERAGE)
    print 'Lidar Coverage layer name:', layer.GetName()

    i = 0
    feature_count = layer.GetFeatureCount()
    # print '', feature_count, ' Features'
    for feature in layer:
        i += 1
        params = {}
        params['uid'] = feature.GetFieldAsInteger('uid')
        params['block_name'] = feature.GetFieldAsString('block_name')
        params['adjusted_l'] = feature.GetFieldAsString('adjusted_l')
        params['sensor'] = feature.GetFieldAsString('sensor')
        params['processor'] = feature.GetFieldAsString('processor')
        params['flight_num'] = feature.GetFieldAsString('flight_num')
        params['mission_na'] = feature.GetFieldAsString('mission_na')
        temp = feature.GetFieldAsString('date_flown')
        if temp != '':
            print 'Temp', temp
            temp_date = datetime.strptime(
                temp, "%Y/%m/%d %H:%M:%S") + timedelta(hours=8)
            print 'Temp date', temp_date
            params['date_flown'] = datetime(
                temp_date.year, temp_date.month, temp_date.day)
        else:
            params['date_flown'] = None
        params['x_shift_m'] = feature.GetFieldAsString('x_shift_m')
        params['y_shift_m'] = feature.GetFieldAsString('y_shift_m')
        params['z_shift_m'] = feature.GetFieldAsString('z_shift_m')
        params['height_dif'] = feature.GetFieldAsString('height_dif')
        params['rmse_val_m'] = feature.GetFieldAsString('rmse_val_m')
        params['cal_ref_pt'] = feature.GetFieldAsString('cal_ref_pt')
        params['val_ref_pt'] = feature.GetFieldAsString('val_ref_pt')
        params['floodplain'] = feature.GetFieldAsString('floodplain')
        params['pl1_suc'] = feature.GetFieldAsString('pl1_suc')
        params['pl2_suc'] = feature.GetFieldAsString('pl2_suc')

        # print params
        print 'Creating object...'
        try:
            obj = create_object(params)
            print '#' * 40
            print i, '/', feature_count
            print 'UID:', obj.uid
            print 'block_name:', obj.block_name
            print 'adjusted_l:', obj.adjusted_l
            print 'sensor:', obj.sensor
            print 'processor:', obj.processor
            print 'flight_num:', obj.flight_num
            print 'mission_na:', obj.mission_na
            print 'date_flown:', obj.date_flown
        except Exception:
            print 'Error creating object!'
            traceback.print_exc()
        # break

# Make button for this
# Dont forget to include update workflow
# lidar_coverage_data()
# print 'Finished all blocks'

# Find block name in coverage
# return block uid
def get_block_pk(blk_path):
    # path format <riverbasin_folder>/Block_name_date/LAS_FILES/
    block_folder_name = blk_path.split('/')[-1]
    if block_folder_name == '':
        block_folder_name = blk_path.split('/')[-2]

    print 'Block Folder Name:', block_folder_name
    temp = block_folder_name.split()
    block_name = ''
    if 'Blk' in block_folder_name
        block_name = block_folder_name.split('_Blk')[0]
    elif 'blk' in block_folder_name
        block_name = block_folder_name.split('_blk')[0]

    return block_name

# Apply rename laz script in cephgeo/utils
# Renaming runs in salad
# NEEDS TRIGGER SCRIPT FOR THIS
def rename_laz(path):
    pass

def get_gridref(renamed):
    pass

def ceph_object_pk(objs):
    pass

def laz_metadata():
    # Parent folder of laz tiles with right block name dir
    # folder_path = '/media/drleviste/MULTIBOOT/DATA/Copied_blocks/Agno/Agno_Blk5C_20130418/'
    folder_path = 'Desktop/Work/DATA/Adjusted_LAZ_Tiles/DREAM/Agno/Agno5C_20130418/'
    renamed_laz = rename_laz(folder_path)

    # Input is parent dir of renamed tiles
    get_gridref(renamed_laz)


    block_pk(folder_path)

    # idk how to get ceph_objs after uploading to lipad
    ceph_objs = ''
    ceph_object_pk(ceph_objs)
# def permute_blk_name(blk_name, rb):
#     # return base case no permutation
#     # add block name
#     strings = blk_name.split('_')
#     print 'Separation:', strings
#     # rb always in foldername
#     get_rb, extra_str = strings[0].split(rb)
#     match = False
#     ind = 0
#     # while match is False or ind < len(blk_name):
#     try:
#         blk_name_match = LidarCoverageBlock.objects.get(block_name=get_rb)
#     except:
#         # no match
#         print 'No match for', get_rb


# def get_block_uid(blk_name, rb):
#     # extract rb from blk_name
#     # match rb first to lidarcoverage blk
#     # must be exact match
#     # append 'blk' to first instance of underscore
#     # join next string before next underscore
#     # check with lidarcoverageblock block_name
#     # join until theres a match
#     right_blk_name = 'Agno_Blk10A'
#     block = LidarCoverageBlock.objects.get(block_name=right_blk_name)
#     return block.uid


# def get_ceph_object(dest):
#     try:
#         ceph_obj = CephDataObject.objects.get(name=dest)
#     except Exception:
#         return 0
#     return ceph_obj.id
# def populate_metadata_store():
#     csv_path = settings.LAZ_RENAMING_LOGS
#     print 'LAZ Log Path:', csv_path

#     print 'Parsing CSV'
#     if not os.path.isfile(csv_path):
#         print '{0} file not found! Exiting.'.format(csv_path)
#         exit(1)

#     with open(csv_path, 'r') as open_file:
#         print 'Opening File'
#         first_line = True
#         counter = 1
#         for line in open_file:

#             print '#' * 80

#             if first_line:
#                 first_line = False
#                 continue

#             tokens = line.strip().split(',')
#             print 'T:', tokens

#             if len(tokens) <= 1:
#                 continue

#             try:
#                 rb = tokens[0].strip()
#                 src = tokens[1].strip()
#                 dest = tokens[2].strip()
#                 date_ = tokens[3].strip()

#                 blk_name = src.split('\')[0]
#                 grid_ref = dest.split('_')
#                 block_uid = get_block_uid(blk_name)
#                 ceph_object = get_ceph_object(dest)

#                 if ceph_object == 0 or block_uid == 0:
#                     print 'No ceph object found for', blk_name
#                     continue
#                 else:
#                     # create object
#                     MetadataStore.objects.create(
#                         ceph_object=ceph_object, grid_ref=grid_ref, block_uid=block_uid)
#             except Exception:
#                 traceback.print_exc()

# TODO
