#!/usr/bin/env python3

# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import argparse
import xml.etree.ElementTree as ET


def replace_repo(doc, old_repo_url, new_repo_url, key):
    did_change = False

    for url in doc.findall('./initvm/mirror/url-list/url'):
        binary = url.find('binary')
        if binary.text.strip().split(' ')[0] != old_repo_url.split(' ')[0]:
            continue
        binary.text = new_repo_url
        url.find('source').text = new_repo_url
        url.find('raw-key').text = '\n' + key + '\n'
        did_change = True

    if not did_change:
        raise Exception('No repository to change was found')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('xml')
    parser.add_argument('old-repo-url')
    parser.add_argument('new-repo-url')
    parser.add_argument('keyfile')

    args = parser.parse_args()

    with open(args.keyfile, 'r') as keyfile:
        key = keyfile.read()

    doc = ET.parse(args.xml)

    replace_repo(
            doc,
            vars(args)['old-repo-url'],
            vars(args)['new-repo-url'],
            key,
    )

    ET.dump(doc)
