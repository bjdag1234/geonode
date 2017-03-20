import geonode.settings as settings
import subprocess

def seed_layers(layer):

    # layer_list = Layer.objects.filter(Q(upload_session__date__month=10)&Q(upload_session__date__day=25)&Q(upload_session__date__year=2016))

    # Test: general_luna_quezon only
    #layer_list = Layer.objects.filter(Q(name__icontains='general_luna_quezon')&Q(upload_session__date__month=10)&Q(upload_session__date__day=25)&Q(upload_session__date__year=2016))

    # for layer in layer_list:
    try:
        out = subprocess.check_output([settings.PROJECT_ROOT + '/gwc.sh', 'seed',
                                       '{0}:{1}'.format(
                                           layer.workspace, layer.name), 'EPSG:900913', '-v', '-a',
                                       settings.OGC_SERVER['default']['USER'] + ':' +
                                       settings.OGC_SERVER['default'][
                                           'PASSWORD'], '-u',
                                       settings.OGC_SERVER['default']['LOCATION'] + 'gwc/rest'],
                                      stderr=subprocess.STDOUT)
        print out
    except subprocess.CalledProcessError as e:
        print 'Error seeding layer:', layer
        print 'e.returncode:', e.returncode
        print 'e.cmd:', e.cmd
        print 'e.output:', e.output
