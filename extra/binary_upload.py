#!/usr/bin/env python3
import argparse
import urllib.request

parser = argparse.ArgumentParser()

parser.add_argument('-url')

args = parser.parse_args()

if args.url:
    urllib.request.urlretrieve(args.url, 'binary')
