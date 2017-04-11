#!/usr/bin/env python

import yaml
from schema import Schema, Optional
import os

def read_config(filename):
    """Read and validate the given configuration file."""
    with open(filename) as f:
        config = yaml.safe_load(f)

    if config == None:
        raise Exception("No config at {}".format(filename))
    return validate(config)

def validate(config):
    """Return normalized config if valid; raise Error if invalid."""
    return config_schema.validate(config)

from rotate import Rotation
from s3_location import S3Location

config_schema = Schema({
    'password': str,
    'rotation': Rotation,
    'local_dir': {
        'path': os.path.exists,
        Optional('extension', default=''): str
    },
    's3_location': S3Location
})

