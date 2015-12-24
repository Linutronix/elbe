#!/usr/bin/env python

from string import split, join

def dos2unix_str (d):
    return join (split (d, '\r\n'), '\n')

def unix2dos_str (d):
    return join (split (dos2unix_str (d), '\n'), '\r\n')

def __rewrite (fn, rw_func):
    with open (fn, 'r+') as f:
        d = rw_func (f.read ())
        f.seek (0)
        f.write (d)
        f.truncate ()

def dos2unix (fn):
    __rewrite (fn, dos2unix_str)

def unix2dos (fn):
    __rewrite (fn, unix2dos_str)
