import geonode.settings as settings

from celery.task import task
from geonode.layers.models import Layer
from layer_metadata import update_metadata
from tag_layers import update_tags

# metadata update, seeding, SUC/FP tagging
@task(name='geonode.tasks.fhm_metadata.update_fhm_metadata_task', queue='fhm_metadata')
def update_fhm_metadata_task(pk):
    layer = Layer.objects.get(pk=pk)
    update_metadata(layer)
    mode = 'fhm'
    update_tags(layer, mode)


@task(name='geonode.tasks.fhm_metadata.tag_fhm_task', queue='fhm_metadata')
def tag_fhm_task(pk):
    layer = Layer.objects.get(pk=pk)
    mode = 'fhm'
    update_tags(layer, mode)

