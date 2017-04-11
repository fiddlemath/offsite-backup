import boto3
import botocore
import os

from schema import Schema

class S3Location:
    """A location (bucket, path-prefix) on AWS S3, with basic access methods.
    
    This assumes that the S3 bucket being accessed isn't versioned.
    """

    _schema = Schema({
        'type': 's3',
        'bucket': str,
        'region': 'us-west-1',
        'path': str,
        'access_key': str,
        'secret_access_key': str
    })
    "The schema for configs for this class."

    # bucket: The boto3 S3 bucket for this location.
    # prefix: The in-bucket path prefix represented by this location.

    @classmethod
    def validate(cls, config):
        return cls._schema.validate(config)
    
    def __init__(self, config):
        self.validate(config)
        self._s3 = boto3.resource(
            's3',
            region_name=config['region'],
            aws_access_key_id = config['access_key'],
            aws_secret_access_key = config['secret_access_key']
        )
        self.bucket_name = config['bucket']
        self.bucket = self._s3.Bucket(self.bucket_name)

        try:
            self._s3.meta.client.head_bucket(Bucket='mybucket')
        except botocore.exceptions.ClientError as e:
            # If a client error is thrown, then check that it was a 404 error.
            # If it was a 404 error, then the bucket does not exist.
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                # Could make the bucket here, instead, perhaps if some forcing flag is given.
                raise e

        self.prefix = config['path']

    def _abs(self, relpath):
        "Produce a bucket-relative path from a location-relative path."
        return os.path.join(self.prefix, relpath)

    def _rel(self, abspath):
        "Produce a location-relative path from a bucket-relative path."
        return os.path.relpath(abspath, self.prefix)
            
    def list(self, path=''):
        "Return a sequence of location-relative paths in this location."
        subdir = os.path.normpath(os.path.join(self.prefix, path))
        keys = self.bucket.objects.filter(Prefix=subdir)

        for key in keys:
            if os.path.normpath(key.key) != subdir:
                yield self._rel(key.key)

    def pull(self, path, filename=None):
        "Pull the S3 file `path` to the local `filename`."
        self.bucket.download_file(self._abs(path), filename)

    def push(self, filename, path=None):
        "Push the local file `filename` to `path` on S3."
        self.bucket.upload_file(filename, self._abs(path))

    def rm(self, *paths):
        "Delete S3 files."
        objects = [{'Key': self._abs(p)} for p in paths]
        self.bucket.delete_objects(Delete = {'Objects': objects})
