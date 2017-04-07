import geonode.settings as settings

from celery.task import task
from geonode.layers.models import Layer
from layer_metadata import update_metadata
from delete_layers import delete_
from tag_layers import update_tags

# metadata update, seeding, SUC/FP tagging
@task(name='geonode.tasks.fhm_metadata.update_fhm_metadata_task', queue='fhm_metadata')
def update_fhm_metadata_task(pk):
    layer = Layer.objects.get(pk=pk)
    update_metadata(layer)
    mode = 'fhm'
    update_tags(layer, mode)

# delete layer (geoserver, geonode+postgis), defeault style
@task(name='geonode.tasks.fhm_metadata.delete_fhm_task', queue='fhm_metadata')
def delete_fhm_task(pk):
    layer = Layer.objects.get(pk=pk)
    delete_(layer)

@task(name='geonode.tasks.fhm_metadata.tag_fhm_task', queue='fhm_metadata')
def tag_fhm_task(pk):
    layer = Layer.objects.get(pk=pk)
    mode = 'fhm'
    update_tags(layer, mode)

