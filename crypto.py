from plumbum.cmd import gpg

def encrypt(password, plainfile, outfile=None):
    if not outfile: outfile = plainfile + '.gpg'
    gpg('--passphrase', password, '--output', outfile, '--yes', '-z', '6', '-c', plainfile)

def decrypt(password, gpgfile, outfile=None):
    if not outfile:
        if gpgfile.endswith('.gpg'):
            outfile = gpgfile[:-4]
        else:
            outfile = gpgfile + '.plain'
    gpg('--passphrase', password, '--output', outfile, '--yes', '-d', gpgfile)
