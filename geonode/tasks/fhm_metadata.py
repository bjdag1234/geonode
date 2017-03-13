import geonode.settings as settings

from celery.task import task
from celery.utils.log import get_task_logger
from geonode.layers.models import Layer
from layer_metadata import update_metadata
import logging

logger = get_task_logger("geonode.tasks.fhm_metadata")
logger.setLevel(logging.INFO)


@task(name='geonode.tasks.fhm_metadata.update_fhm_metadata_task', queue='fhm_metadata')
def update_fhm_metadata_task(pk):
    layer = Layer.objects.get(pk=pk)
    update_metadata(layer)
