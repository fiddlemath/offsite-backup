A small toolset for mirroring local backups to S3, with encryption and rotation.

This isn't properly packaged or anything. It's a little project still.

# Setup

- `pip install` these python packages: schema, pyyaml, plumbum, boto3
- Ensure that the `gpg` command is installed.
- Put together a config file

# Config Format
Config files are in YAML, and roughly match the following schema:


    password: <string>

    rotation:
        days: <int or 'all'>
        weeks: <int or 'all'>
        months: <int or 'all'>
        years: <int or 'all'>

    local_dir:
        path: <local dir>
        extension: <ext>  # Optional

    s3_location:
        type: s3
        bucket: <bucket name>
        region: us-west-1
        path: <path inside bucket>
        access_key: <str>
        secret_access_key: <str>

`password` is the passphrase that GPG will use to symmetrically encrypt all data. Store this somewhere!
