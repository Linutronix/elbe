#!/usr/bin/env python3
# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2025 Linutronix GmbH

"""
Perform release steps in the ELBE source repository.
"""

import datetime
import enum
import functools
import pathlib
import subprocess
import textwrap

from debian.changelog import Changelog
from debian.deb822 import Deb822, PkgRelation, _PkgRelationMixin


def debian_version(base, debian_release=None):
    if debian_release is None:
        return str(base)
    return f'{base}~bpo{debian_release.version}'


def get_current_version():
    cl = Changelog()
    with open('debian/changelog') as f:
        cl.parse_changelog(f)

    return cl.get_version()


def update_changelog(version, debian_release, release_notes):
    cl = Changelog()
    with open('debian/changelog') as f:
        cl.parse_changelog(f)

    cl.new_block(
            package=cl.package,
            version=debian_version(version),
            distributions=str(debian_release),
            urgency=cl.urgency,
            changes=[
                '',
                '  * Team upload',
                f'  * Release notes in {release_notes}',
                '',
                ],
            author=cl.author,
            date=cl.date,
     )

    with open('debian/changelog', 'w') as f:
        cl.write_to_open_file(f)


def update_changelog_backport(debian_release):
    cl = Changelog()
    with open('debian/changelog') as f:
        cl.parse_changelog(f)

    current = cl.get_version()

    cl.new_block(
            package=cl.package,
            version=debian_version(current, debian_release),
            distributions=str(debian_release),
            urgency=cl.urgency,
            changes=[
                '',
                '  * Team upload',
                f'  * Rebuild for {debian_release}',
                '',
                ],
            author=cl.author,
            date=cl.date,
     )

    with open('debian/changelog', 'w') as f:
        cl.write_to_open_file(f)


@functools.total_ordering
class StripRestrictionResult(enum.Enum):
    NONE = enum.auto()
    KEEP = enum.auto()
    DISCARD = enum.auto()

    def __gt__(self, other):
        return self.value > other.value


class StripDistRestrictions:
    def __init__(self, dist):
        self.dist = dist

    def __call__(self, relations):
        return self._visit_relations(relations)

    # The hierarchy:
    # relations = list[outer_relation]
    # outer_relation = list[inner_relation]
    # inner_relation = dict[restrictions=restriction]
    # restrictions = list[outer_restriction]
    # outer_restriction = list[inner_restriction]
    # inner_restriction = Restriction

    @staticmethod
    def __remove_falsy(es):
        return [e for e in es if e]

    def _visit_relations(self, relations):
        return self.__remove_falsy([
            self._visit_outer_relation(outer_relation)
            for outer_relation
            in relations
        ])

    def _visit_outer_relation(self, outer_relation):
        return self.__remove_falsy([
            self._visit_inner_relation(inner_relation)
            for inner_relation
            in outer_relation
        ])

    def _visit_inner_relation(self, inner_relation):
        restrictions = inner_relation.get('restrictions')
        if not restrictions:
            return inner_relation

        inner_relation = inner_relation.copy()
        result, restrictions = self._visit_restrictions(restrictions)

        if result == StripRestrictionResult.DISCARD:
            return None

        inner_relation['restrictions'] = restrictions or None
        return inner_relation

    def _visit_restrictions(self, restrictions):
        outers = [
            self._visit_outer_restriction(outer_restriction)
            for outer_restriction
            in restrictions
        ]

        result = StripRestrictionResult.NONE
        ret = []

        for r, i in outers:
            if r == StripRestrictionResult.KEEP:
                continue
            result = max(result, r)
            ret.append(i)

        return result, ret or None

    def _visit_outer_restriction(self, outer_restriction):
        inners = [
            self._visit_inner_restriction(inner_restriction)
            for inner_restriction
            in outer_restriction
        ]

        result = StripRestrictionResult.NONE
        ret = []

        for r, i in inners:
            result = max(result, r)
            ret.append(i)

        return result, ret or None

    def _visit_inner_restriction(self, inner_restriction):
        if not inner_restriction.profile.startswith('dist.'):
            return StripRestrictionResult.NONE, inner_restriction
        elif (inner_restriction.profile == f'dist.{self.dist}') == inner_restriction.enabled:
            return StripRestrictionResult.KEEP, inner_restriction
        else:
            return StripRestrictionResult.DISCARD, inner_restriction


def strip_release_restrictions(relations, release):
    return StripDistRestrictions(release)(relations)


def test_strip_release_restriction_include():
    import textwrap

    test_data = textwrap.dedent("""
    dep1, dep2 <dep2profile>, dep3 <!dist.bullseye>, dep4 <dist.bullseye>
    """)

    relations = PkgRelation.parse_relations(test_data)
    relations = strip_release_restrictions(relations, 'bullseye')
    assert PkgRelation.str(relations) == 'dep1, dep2 <dep2profile>, dep4'


def test_strip_release_restriction_exclude():
    import textwrap

    test_data = textwrap.dedent("""
    dep1, dep2 <dep2profile>, dep3 <!dist.bullseye>, dep4 <dist.bullseye>
    """)

    relations = PkgRelation.parse_relations(test_data)
    relations = strip_release_restrictions(relations, 'buster')
    assert PkgRelation.str(relations) == 'dep1, dep2 <dep2profile>, dep3'


class DebianControl(Deb822, _PkgRelationMixin):
    _relationship_fields = [
        'build-depends',
    ]

    def __init__(self, *args, **kwargs):
        Deb822.__init__(self, *args, **kwargs)
        _PkgRelationMixin.__init__(self, *args, **kwargs)


def update_control(release):
    with open('debian/control') as f:
        paragraphs = list(DebianControl.iter_paragraphs(f))

    for paragraph in paragraphs:
        bds = paragraph.relations['build-depends']
        if not bds:
            continue

        paragraph['build-depends'] = PkgRelation.str(
            strip_release_restrictions(bds, release),
        ).replace(', ', ',\n  ')

    with open('debian/control', 'w') as f:
        for i, paragraph in enumerate(paragraphs):
            if i:
                f.write('\n')
            paragraph.dump(f, text_mode=True)


def update_version_py_remove_dev0(current_version, new_version):
    with open('elbepack/version.py') as f:
        source = f.read()

    source = source.replace(f"'{current_version}'", f"'{new_version}'")

    new_source = source

    source = source.replace(textwrap.dedent("""
    if is_devel:
        elbe_version += '.dev0'
    """), '\n')

    with open('elbepack/version.py', 'w') as f:
        f.write(source)

    return new_source


def update_version_py_add_dev0(source):
    with open('elbepack/version.py', 'w') as f:
        f.write(source)


def create_release_notes(version):
    date = datetime.date.today().isoformat()
    subprocess.check_call(['towncrier', 'build', '--version', version, '--date', date])
    release_notes = pathlib.Path(f'docs/news/{date}-v{version}.rst')
    if not release_notes.is_file():
        raise ValueError(f'release notes where not created at {release_notes}')
    return release_notes


def create_commit(message):
    subprocess.check_call(['git', 'commit', '-a', '-s', '-m', message])


def create_release_tags(version, debian_release=None):
    # public, backwards compatible tag
    v = f'v{version}' if debian_release is None else f'v{version}_{debian_release}'
    subprocess.check_call(['git', 'tag', '--sign', '-m', f'release: {v}', f'{v}'])

    # structured tag for Linutronix automation
    v = debian_version(version, debian_release).replace('~', '_')
    subprocess.check_call(['git', 'tag', '--sign', '-m', f'release: {v}', f'releases/rebase/{v}'])


def create_release_branch(version, debian_release=None):
    if debian_release is None:
        branch = f'releases/v{version}'
    else:
        branch = f'releases/v{version}_{debian_release}'

    subprocess.check_call(['git', 'checkout', '-b', branch])


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('version', help='New version to release')
    parser.add_argument('release', help='Primary targeted Debian release')
    parser.add_argument('backports', nargs='+',
                        help='Additional Debian releases to create backports for')
    args = parser.parse_args()

    # Make sure the repository is clean
    subprocess.check_call(['git', 'diff', '--exit-code'])
    subprocess.check_call(['git', 'checkout', 'for-master'])

    current_version = get_current_version()
    version = args.version
    release = args.release

    new_version_py = update_version_py_remove_dev0(current_version, version)
    release_notes = create_release_notes(version)
    update_changelog(version, release, release_notes)
    create_commit(f'release: v{version}')
    create_release_tags(version)
    create_release_branch(version)

    for backport in args.backports:
        subprocess.check_call(['git', 'checkout', f'v{version}'])
        create_release_branch(version, backport)
        update_changelog_backport(backport)
        update_control(backport)
        create_commit(f'release: v{version} {backport} backport')
        create_release_tags(version, backport)

    subprocess.check_call(['git', 'checkout', 'for-master'])
    update_version_py_add_dev0(new_version_py)
    create_commit('release: back to development')
