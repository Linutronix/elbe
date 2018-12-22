# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2014 Torben Hohn <torbenh@linutronix.de>
# Copyright (c) 2017 Manuel Traut <manut@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later

suite2codename = {'oldoldoldstable': 'squeeze',
                  'oldoldstable': 'wheezy',
                  'oldstable': 'jessie',
                  'stable': 'stretch',
                  'testing': 'buster',
                  'unstable': 'sid',

                  'lucid': 'lucid',
                  'precise': 'precise',
                  'quantal': 'quantal',
                  'raring': 'raring',
                  'saucy': 'saucy',
                  'trusty': 'trusty',
                  'utopic': 'utopic',
                  'vivid': 'vivid',
                  'wily': 'wily',
                  'xenial': 'xenial',
                  'yakkety': 'yakkety',
                  'zesty': 'zesty',
                  'artful': 'artful',
                  'bionic': 'bionic',
                  'cosmic': 'cosmic',
                 }


# generate reverse mapping
codename2suite = {v: k for k, v in suite2codename.items()}
