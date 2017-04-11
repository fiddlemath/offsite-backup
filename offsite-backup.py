#!/usr/bin/env python
""" offsite-backup.py

This script takes a local-backup directory and a remote backup destination,
encrypts and remotely stores new, recent local backups.
"""

from plumbum import cli
from plumbum.cmd import tar
from config import read_config
from rotate import Rotation
from s3_location import S3Location
from crypto import encrypt, decrypt

from tempfile import mkdtemp
from os import path, listdir
from shutil import rmtree, make_archive, move
from contextlib import contextmanager

class App(cli.Application):
    DESCRIPTION = "Handle replicating our backups offsite."
    PROGNAME = "offsite-backup"
    VERSION = "0.1"

    conf_filename = cli.SwitchAttr(
        ["-c", "--conf"],
        cli.ExistingFile,
        default = path.expanduser("~/.config/offsite-backup.yaml")
    )
    "The location of the offsite-confluence-backup configuration."
    
    conf = None
    "The parsed configuration of this app"

    def main(self):
        self.conf = read_config(self.conf_filename)
        self.rotation = Rotation(self.conf['rotation'])
        self.s3_loc = S3Location(self.conf['s3_location'])
        # Note that this last has mild AWS-interaction side effects.
        # If I add commands that do not need to interact with S3,
        # then defer this init.

# Tiny assistant
def strip_extension(ext, s):
    if len(ext) <= 0: return s
    elif s.endswith(ext): return s[:-len(ext)]
    else: return s

def strip_extensions(s):
    return s.split('.', 1)[0]

@contextmanager
def tempdir():
    """On entry, makes a clean, temporary directory and yields that path.
    On exit, removes that directory and everything in it."""
    tmpdir = mkdtemp()
    yield tmpdir
    rmtree(tmpdir)
        
@App.subcommand("list")
class ListApp(cli.Application):
    DESCRIPTION = "List all available backup files"
    def main(self):
        paths = self.parent.s3_loc.list()
        for p in paths:
            print p

@App.subcommand("restore")
class RestoreApp(cli.Application):
    DESCRIPTION = "Fetch the named backup file; by default, fetch the most recent."
    def main(self, backup_name=None):
        s3_loc = self.parent.s3_loc
        paths = s3_loc.list()

        if backup_name==None:
            pl = list(paths)
            if len(pl) <= 0:
                pl.sort(reverse=True)
                backup_name = pl[0]
            else:
                raise Exception('The S3 Location has no backups to restore.')
        
        elif backup_name not in paths:
            raise Exception('"{}" is not at the S3 Location. Check offsite-backup.py list' .
                                format(backup_name))

        # Save to a temporary location. Decrypt and untar as needed.
        with tempdir() as tmp_path:
            tmp_path = mkdtemp()
            tmp_fn = path.join(tmp_path, backup_name)
            s3_loc.pull(backup_name, tmp_fn)

            if tmp_fn.endswith('.gpg'):
                decrypt(self.parent.conf['password'], tmp_fn, tmp_fn[:-4])
                tmp_fn = strip_extension('.gpg', tmp_fn)

            if tmp_fn.endswith('.tar'):
                tar('xf', tmp_fn)

            else:
                move(tmp_fn, path.basename(tmp_fn))
            

@App.subcommand("test")
class TestApp(cli.Application):
    DESCRIPTION = "Test the specified configuration."
    def main(self):
        # Actually, this should kind of just happen.
        pass

@App.subcommand("backup")
class BackupApp(cli.Application):
    DESCRIPTION = """Encrypt and push new local files, and cull remote files to cull,
    all according to the configured rotation policy."""

    def main(self):
        # List backups from the S3 location
        s3_loc = self.parent.s3_loc
        s3_paths = s3_loc.list()

        # List backups from local storage
        local_dir = self.parent.conf['local_dir']['path']

        local_paths = listdir(local_dir)

        # Pick backups to push according to the rotation policy.
        rotation = self.parent.rotation
        (local_keep, local_drop, local_invalid) = rotation.filter(local_paths)

        if local_invalid:
            print "Ignoring invalid backup filenames: " +\
              ', '.join(local_invalid)

        keep_stems = [strip_extensions(fname) for fname in local_keep]
        # keep_stems[i] is the stem of local_keep[i]
        s3_stems = [strip_extensions(fname) for fname in s3_paths]
        push_stems = set(keep_stems) - set(s3_stems)

        to_push = [local_keep[keep_stems.index(stem)]
                       for stem in push_stems]
            
        # Encrypt and push each selected file.
        with tempdir() as tmp_path:
            for f in to_push:
                local_f = path.join(local_dir, f)

                # If the file's actually a directory, tar it up first.
                if path.isdir(local_f):
                    # make tarfile inside tmp_path.
                    tar_basename = path.join(tmp_path, f)
                    local_f = make_archive(tar_basename, 'tar',
                                            root_dir=local_dir,
                                            base_dir=f)
                    f += '.tar'

                f_gpg = f + ".gpg"
                tmp_f = path.join(tmp_path, f_gpg)
                
                encrypt(self.parent.conf['password'], local_f, tmp_f)
                s3_loc.push(tmp_f, f_gpg)
            
        # Pare S3 entries according to the rotation policy
        (s3_keep, s3_drop, s3_invalid) = rotation.filter(s3_loc.list())

        for p in s3_drop:
            s3_loc.rm(p)
    
if __name__ == "__main__":
    App.run()
