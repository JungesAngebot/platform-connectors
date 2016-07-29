#!/usr/bin/env python3
import argparse
import urllib.request

import sys


def reporthook(blocknum, blocksize, totalsize):
    readsofar = blocknum * blocksize
    if totalsize > 0:
        percent = readsofar * 1e2 / totalsize
        s = "\r%5.1f%% %*d / %d" % (
            percent, len(str(totalsize)), readsofar, totalsize)
        sys.stderr.write(s)
        if readsofar >= totalsize:  # near the end
            sys.stderr.write("\n")
    else:  # total size is unknown
        sys.stderr.write("read %d\n" % (readsofar,))


parser = argparse.ArgumentParser()

parser.add_argument('-url')

args = parser.parse_args()

if args.url:
    urllib.request.urlretrieve(args.url, 'binary', reporthook)
