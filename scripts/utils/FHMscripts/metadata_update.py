from geonode.settings import GEONODE_APPS
import geonode.settings as settings
import os

from datetime import datetime, timedelta
from django.contrib.auth.models import Group
from django.db.models import Q
from geonode.base.models import TopicCategory
from geonode.cephgeo.models import RIDF
from geonode.layers.models import Layer, Style
from geoserver.catalog import Catalog
from guardian.shortcuts import assign_perm, get_anonymous_user
from pprint import pprint
from threading import Thread
import multiprocessing
import subprocess
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geonode.settings")


def update_style(layer, style_template):

    # Get geoserver catalog
    cat = Catalog(settings.OGC_SERVER['default']['LOCATION'] + 'rest',
                  username=settings.OGC_SERVER['default']['USER'],
                  password=settings.OGC_SERVER['default']['PASSWORD'])

    # Get equivalent geoserver layer
    gs_layer = cat.get_layer(layer.name)
    print layer.name, ': gs_layer:', gs_layer.name

    # Get current style
    # pprint(dir(gs_layer))
    cur_def_gs_style = gs_layer._get_default_style()
    # pprint(dir(cur_def_gs_style))
    if cur_def_gs_style is not None:
        print layer.name, ': cur_def_gs_style.name:', cur_def_gs_style.name

    # Get proper style
    attributes = [a.attribute for a in layer.attributes]
    gs_style = None
    if '_fh' in layer.name:
        if 'Var' in attributes:
            gs_style = cat.get_style(style_template)
        elif 'Merge' in attributes:
            gs_style = cat.get_style("fhm_merge")
        elif 'UVar' in attributes:
            gs_style = cat.get_style('fhm_uvar')
    else:
        gs_style = cat.get_style(style_template)

    # has_layer_changes = False
    try:
        if gs_style is not None:
            print layer.name, ': gs_style.name:', gs_style.name

            if cur_def_gs_style and cur_def_gs_style.name != gs_style.name:

                print layer.name, ': Setting default style...'
                gs_layer._set_default_style(gs_style)
                cat.save(gs_layer)

                print layer.name, ': Deleting old default style from geoserver...'
                cat.delete(cur_def_gs_style)

                print layer.name, ': Deleting old default style from geonode...'
                gn_style = Style.objects.get(name=layer.name)
                gn_style.delete()

            # set_style = False
            # try:
            #     if layer.sld_body != gs_style.sld_body:
            #         set_style = True
            #         print layer.name, ': layer.sld_body:'
            #         pprint(layer.sld_body)
            #         print layer.name, ': gs_style.sld_body:'
            #         pprint(gs_style.sld_body)
            # except AttributeError:
            #     print layer.name, ': AttributeError!'
            #     set_style = True

            # if set_style:
            #     print layer.name, ': Setting layer.sld_body...'
            #     has_layer_changes = True
            #     layer.sld_body = gs_style.sld_body

    except Exception:
        print layer.name, ': Error setting style!'
        traceback.print_exc()
        raise

    # return has_layer_changes


def update_thumb_perms(layer):

    print layer.name, ': Setting thumbnail permissions...'
    thumbnail_str = 'layer-' + str(layer.uuid) + '-thumb.png'
    thumb_url = '/var/www/geonode/uploaded/thumbs/' + thumbnail_str
    subprocess.call(['sudo', '/bin/chown', 'www-data:www-data', thumb_url])
    subprocess.call(['sudo', '/bin/chmod', '666', thumb_url])


def update_layer_perms(layer):

    try:

        print layer.name, ': Updating layer permissions...'
        layer.remove_all_permissions()
        anon_group = Group.objects.get(name='anonymous')
        assign_perm('view_resourcebase', anon_group, layer.get_self_resource())
        assign_perm('download_resourcebase', anon_group,
                    layer.get_self_resource())
        assign_perm('view_resourcebase', get_anonymous_user(),
                    layer.get_self_resource())
        assign_perm('download_resourcebase', get_anonymous_user(),
                    layer.get_self_resource())

    except Exception:
        print layer.name, ': Error updating layer permissions!'
        traceback.print_exc()
        # raise


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
    update_style(layer, 'fhm')

    # Update thumbnail permissions
    update_thumb_perms(layer)

    # Update layer permissions
    update_layer_perms(layer)

    # update_layer_perms_thread = Thread(target=update_layer_perms,
    #                                    args=(layer,))
    # update_layer_perms_thread.start()

    # pool.apply_async(update_layer_perms, (layer,))

    return has_layer_changes


def save_layer(layer):
    print layer.name, ': Saving layer...'
    layer.save()


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


if __name__ == "__main__":

    # Get FHM layers uploaded within the past week
    #lastweek = datetime.now() - timedelta(days=7)
    # Get FHM layers uploaded within the past 2 days
    lastday = datetime.now() - timedelta(days=2)
    layers = Layer.objects.filter(
        Q(name__iregex=r'^ph[0-9]+_fh') &
        Q(upload_session__date__gte=lastday))

    total = len(layers)
    print 'Updating', total, 'layers!'

    # Initialize pool
    # pool = multiprocessing.Pool(2)

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

    # if haschanges:
    #     print 'Has changes! Breaking...'
    # break

    # Update metadata in parallel
    # pool.map_async(update_metadata, layers)
    # pool.close()
    # pool.join()
