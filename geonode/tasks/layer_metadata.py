from celery import task, group
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from django.db.models import Q
from geonode.base.models import TopicCategory
from geonode.cephgeo.models import RIDF
from geonode.layers.models import Layer
from layer_permission import fhm_perms_update
from layer_style import style_update
import subprocess
import getpass
import multiprocessing
import traceback
logger = get_task_logger("geonode.tasks.update")


def own_thumbnail(layer):
    print 'USER', getpass.getuser()
    print layer.name, ': Setting thumbnail permissions...'
    thumbnail_str = 'layer-' + str(layer.uuid) + '-thumb.png'
    thumb_url = '/var/www/geonode/uploaded/thumbs/' + thumbnail_str
    subprocess.call(['sudo', '/bin/chown', 'www-data:www-data', thumb_url])
    subprocess.call(['sudo', '/bin/chmod', '666', thumb_url])


def update_fhm(layer):

    # Get flood year from layer name
    flood_year = int(layer.name.split('fh')[1].split('yr')[0])
    print layer.name, ': flood_year:', flood_year

    # Get flood year probability
    flood_year_probability = int(100 / flood_year)
    print layer.name, ': flood_year_probability:', flood_year_probability

    # Get map resolution
    map_resolution = ''
    if "_10m_30m" in layer.name:
        map_resolution = '30'
    elif "_10m" in layer.name:
        map_resolution = '10'
    elif "_30m" in layer.name:
        map_resolution = '30'
    print layer.name, ': map_resolution:', map_resolution

    # Get muni code
    muni_code = layer.name.split('_fh')[0]
    print layer.name, ': muni_code:', muni_code

    # Get ridf
    ridf_obj = RIDF.objects.get(muni_code__icontains=muni_code)
    ridf = eval('ridf_obj._' + str(flood_year) + 'yr')
    print layer.name, ': ridf: ', ridf

    # Get proper layer properties
    # Title
    layer_title = ''
    muni = ridf_obj.muni_name
    prov = ridf_obj.prov_name
    layer_title = '{0}, {1} {2} Year Flood Hazard Map'.format(
        muni, prov, flood_year).replace("_", " ").title()
    if ridf_obj.iscity:
        layer_title = 'City of ' + layer_title
    print layer.name, ': layer_title:', layer_title

    # Abstract
    layer_abstract = """This shapefile, with a resolution of {0} meters, illustrates the inundation extents in the area if the actual amount of rain exceeds that of a {1} year-rain return period.

Note: There is a 1/{2} ({3}%) probability of a flood with {4} year return period occurring in a single year. The Rainfall Intesity Duration Frequency is {5}mm.

3 levels of hazard:
Low Hazard (YELLOW)
Height: 0.1m-0.5m

Medium Hazard (ORANGE)
Height: 0.5m-1.5m

High Hazard (RED)
Height: beyond 1.5m""".format(map_resolution, flood_year, flood_year,
                              flood_year_probability, flood_year, ridf)
    print layer.name, ': layer_abstract:', layer_abstract

    # Purpose
    layer_purpose = " The flood hazard map may be used by the local government for appropriate land use planning in flood-prone areas and for disaster risk reduction and management, such as identifying areas at risk of flooding and proper planning of evacuation."
    print layer.name, ': layer_purpose:', layer_purpose

    # pprint(layer.category)
    # pprint(layer.keywords)

    # Check if there are changes
    has_layer_changes = False
    if layer.title != layer_title:
        print layer.name, ': Setting layer.title...'
        has_layer_changes = True
        layer.title = layer_title
    if layer.abstract != layer_abstract:
        print layer.name, ': Setting layer.abstract...'
        has_layer_changes = True
        layer.abstract = layer_abstract
    if layer.purpose != layer_purpose:
        print layer.name, ': Setting layer.purpose...'
        has_layer_changes = True
        layer.purpose = layer_purpose
    # print dir(layer.keywords)
    # pprint(layer.keywords.values_list()[0])
    if len(layer.keywords.values_list()) == 0 or 'Flood Hazard Map' not in layer.keywords.values_list()[0]:
        print layer.name, ': Adding keyword...'
        has_layer_changes = True
        layer.keywords.add("Flood Hazard Map")
    if layer.category != TopicCategory.objects.get(identifier="geoscientificInformation"):
        print layer.name, ': Setting layer.category...'
        has_layer_changes = True
        layer.category = TopicCategory.objects.get(
            identifier="geoscientificInformation")

    # Update style
    style_update(layer, 'fhm')

    # Update thumbnail permissions
    own_thumbnail(layer)

    # Update layer permissions
    fhm_perms_update(layer)

    return has_layer_changes


def update_metadata(layer):

    print 'layer.name:', layer.name

    #
    # FHM
    #
    try:
        has_layer_changes = False
        if '_fh' in layer.name:
            has_layer_changes = update_fhm(layer)

        # Save layer if there are changes
        if has_layer_changes:
            print layer.name, ': Saving layer...'
            layer.save()

            # save_layer_thread = Thread(target=save_layer, args=(layer,))
            # save_layer_thread.start()

            # pool.apply_async(save_layer, (layer,))
        else:
            print layer.name, ': No changes to layer. Skipping...'

    except Exception:
        print layer.name, ': Error updating metadata!'
        traceback.print_exc()
        # raise

    return has_layer_changes

def fhm_year_metadata(flood_year):
    # layer_list = []

    # Get FHM layers uploaded within the past 2 days
    lastday = datetime.now() - timedelta(days=2)
    layers = Layer.objects.filter(
        Q(name__iregex=r'^ph[0-9]+_fh') &
        Q(name__icontains=flood_year) &
        Q(upload_session__date__gte=lastday))

    total = len(layers)
    print 'Updating', total, 'layers!'

    # Update metadata
    counter = 0
    start_time = datetime.now()
    for layer in layers:
        print '#' * 40

        update_metadata(layer)

        counter += 1
        duration = datetime.now() - start_time
        total_time = duration.total_seconds() * total / float(counter)
        print counter, '/', total, 'ETA:', start_time + timedelta(seconds=total_time)


    # for layer in layers:
    #     layer_list.append((layer, flood_year, flood_year_probability))
    # pool = multiprocessing.Pool()
    # pool.map_async(_update, layer_list)
    # pool.close()
    # pool.join()
