# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import os
import pathlib

from docutils import nodes
from docutils.parsers.rst import directives

import packaging.version

from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles


__here__ = pathlib.Path(__file__).parent


def _versioned_doc_url(version):
    return 'https://elbe-rfs.org/docs/sphinx/v{}/index.html'.format(version)


def _docs_directory(config):
    docs_directory = config.elbedocoverview_docs_directory
    if docs_directory is None:
        raise ExtensionError('Missing configuration "elbedocoverview_docs_directory"')

    return docs_directory


class _ElbeDocOverview(SphinxDirective):

    def run(self):
        self.env.note_dependency(__file__)

        docs_directory = _docs_directory(self.config)

        versions = os.listdir(docs_directory)
        versions = filter(lambda v: v.startswith('v'), versions)
        versions = map(lambda v: v.removeprefix('v'), versions)
        versions = sorted(versions, reverse=True, key=lambda v: packaging.version.Version(v))

        items = nodes.bullet_list(classes=['elbe-website-version-list'])

        for version in versions:
            list_item = nodes.list_item()
            par = nodes.paragraph()
            contents = f'v{version}'
            ref = nodes.reference(contents, contents,
                                  refuri=_versioned_doc_url(version))
            par += ref
            list_item += par
            items += list_item

        return [items]


class section_level(nodes.Element):
    def get_level(self):
        return self['level']


def visit_section_level_node(self, node):
    self.section_level += node.get_level()


def depart_section_level_node(self, node):
    self.section_level -= node.get_level()


class _ElbeContainerWithTitles(SphinxDirective):
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True
    option_spec = {
        'section_level_adjust': int,
    }

    def run(self):
        n = nodes.container(
                classes=directives.class_option(self.arguments[0] or ''),
        )
        nested_parse_with_titles(state=self.state, content=self.content,
                                 content_offset=self.content_offset, node=n)

        section_level_adjust = self.options.get('section_level_adjust')
        if not section_level_adjust:
            return [n]

        sl = section_level(level=section_level_adjust)
        sl += n
        return [sl]


def _config_inited(app, config):
    if 'intersphinx_mapping' not in config:
        raise ExtensionError('missing intersphinx extension')

    docs_directory = _docs_directory(config)

    config.intersphinx_mapping['elbe'] = (
            f'https://elbe-rfs.org/docs/sphinx/v{config.version}/',
            f'{docs_directory}/v{config.version}/objects.inv',
    )


def setup(app):
    app.add_config_value('elbedocoverview_docs_directory', None, 'env', str)
    app.add_directive('elbedocoverview', _ElbeDocOverview)
    app.add_directive('elbe-container-with-titles', _ElbeContainerWithTitles)
    app.add_node(section_level, html=(visit_section_level_node, depart_section_level_node))
    app.connect('config-inited', _config_inited)
    app.add_css_file('elbe-website.css')

    return {
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
