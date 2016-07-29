#!/usr/bin/env python3
import argparse
import urllib.request

import sys


def reporthook(block_num, block_size, total_size):
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = read_so_far * 1e2 / total_size
        s = '\r%5.1f%% %*d / %d' % (
            percent, len(str(total_size)), read_so_far, total_size)
        sys.stderr.write(s)
        if read_so_far >= total_size:
            sys.stderr.write('\n')
    else:
        sys.stderr.write('read %d\n' % (read_so_far,))


parser = argparse.ArgumentParser()

parser.add_argument('-url')

args = parser.parse_args()

if args.url:
    urllib.request.urlretrieve(args.url, 'binary', reporthook)
