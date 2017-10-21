import boto,boto.s3.connection, warnings, os, mimetypes, logging
from boto.s3.key import Key
from pprint import pprint
from os import listdir
from os.path import isfile, join
from dateutil.parser import parse

original_filters = warnings.filters[:]

# Ignore warnings.
warnings.simplefilter("ignore")

#~ try:
    #~ pass
#~ finally:
    #~ warnings.filters = original_filters
    
class CephS3StorageClient(object):
    
    def __init__(self, user, access_key, secret_key, ceph_radosgw_url, container_name=None):
        self.user = user
            
        self.access_key = access_key
        
        self.secret_key = secret_key
        
        self.ceph_radosgw_url = ceph_radosgw_url
        
        self.connection = self.__connect()
        
        self.active_container_name = container_name
        
        self.log = self.log_wrapper()

    
    def __connect(self):
        return  boto.connect_s3(
        aws_access_key_id = self.access_key,
        aws_secret_access_key = self.secret_key,
        host = self.ceph_radosgw_url,
        is_secure=False,
        calling_format = boto.s3.connection.OrdinaryCallingFormat(),
        )
    
    def list_containers(self):
        pprint(self.connection.get_all_buckets())
        return self.connection.get_all_buckets()
    
    def set_active_container(self, container_name):
        self.active_container_name =  container_name
    
    def get_active_container(self):
        return self.active_container_name
    
    def list_files(self, container_name=None):
        if container_name is not None:
            b =  self.connection.get_bucket(container_name)
            keys = b.get_all_keys()
            #map attributes to dict
            cephobjects = []
            for key in keys:
                cephobjects.append(dict(name=key.name, last_modified=parse(key.last_modified,fuzzy=True),bytes=key.size,hash=key.md5,content_type=key.content_type))

            return list(cephobjects)

        else:
            b =  self.connection.get_bucket(container_name)
            keys = b.get_all_keys()
            #map attributes to dict
            cephobjects = []
            for key in keys:
                cephobjects.append(dict(name=key.name, last_modified=parse(key.last_modified,fuzzy=True),bytes=key.size,hash=key.md5,content_type=key.content_type))

            return list(cephobjects)
    
    def delete_object(self, object_name, container=None):
        if container is None:
            container = self.active_container_name
        b = self.connection.get_bucket(container)
        b.delete_key(object_name)

    def upload_file_from_path(self, file_path, container=None):
        file_name = os.path.basename(file_path)
        if container is None:
            container = self.active_container_name
        #file_id_name = file_name.split(".")[0]
        
        content_type="None"
        try:
            content_type = mimetypes.types_map["."+file_name.split(".")[-1]]
        
        except KeyError:
            pass
        
        self.log.info("Uploading  file {0} [size:{1} | type:{2}]...".format( file_name,
                                                                        os.stat(file_path).st_size,
                                                                        content_type))
        b = self.connection.get_bucket(container)
        k = Key(b)
        k.key = file_name
        with open(file_path, 'r') as file_obj:
            k.set_contents_from_filename(file_obj)         
    
    def upload_via_http(self):
        pass
    
    def download_file_to_path(self, object_name, destination_path, container=None):
        obj_tuple = self.connection.get_object(self.active_container_name, object_name)
        file_path = join(destination_path,object_name)
        if container is None:
            container = self.active_container_name
    
        b = self.connection.get_bucket(container)
        k = Key(b)
        k.key = object_name
        with open(file_path, 'r') as file_obj:
            k.get_contents_to_filename(file_obj)         
     
        self.log.info("Finished downloading to [{0}]. Wrote [{1}] bytes...".format(  file_path,
                                                                                os.stat(file_path).st_size,))
    
    def download_via_http(self):
        pass
    
    def close_connection(self):
        self.connection.close()
    
    def get_cwd(self):
        """
            Returns the current working directory of the python script
        """
        path = os.path.realpath(__file__)
        if "?" in path:
            return path.rpartition("?")[0].rpartition("/")[0]+"/"
        else:
            return path.rpartition("/")[0]+"/"
    
    def log_wrapper(self):
        """
        Wrapper to set logging parameters for output
        """
        # Initialize logging
        logging.basicConfig(filename=self.get_cwd()+'logs/ceph_storage.log',level=logging.DEBUG)
        self.LOGGING = True
        log = logging.getLogger('client.py')
        
        # Set the log format and log level
        log.setLevel(logging.DEBUG)
        #log.setLevel(logging.INFO)

        # Set the log format.
        stream = logging.StreamHandler()
        logformat = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%b %d %H:%M:%S')
        stream.setFormatter(logformat)

        log.addHandler(stream)
        return log

