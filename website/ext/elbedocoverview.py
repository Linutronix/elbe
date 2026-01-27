# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import os
import pathlib
import xml.sax.saxutils

from docutils import nodes
from docutils.parsers.rst import directives

import packaging.version

from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective
from sphinx.util.inventory import InventoryFile
from sphinx.util.nodes import nested_parse_with_titles


__here__ = pathlib.Path(__file__).parent


def _versioned_doc_url(version):
    return 'https://elbe-rfs.org/docs/sphinx/v{}/index.html'.format(version)


def _versioned_doc_directory(version):
    return 'https://elbe-rfs.org/docs/sphinx/v{}/'.format(version)


def _docs_directory(config):
    docs_directory = config.elbedocoverview_docs_directory
    if docs_directory is None:
        raise ExtensionError('Missing configuration "elbedocoverview_docs_directory"')

    return docs_directory


def _docs_versions(config):
    docs_directory = _docs_directory(config)

    versions = os.listdir(docs_directory)
    versions = filter(lambda v: v.startswith('v'), versions)
    versions = map(lambda v: v.removeprefix('v'), versions)
    versions = sorted(versions, reverse=True, key=lambda v: packaging.version.Version(v))

    return versions


class _ElbeDocOverview(SphinxDirective):

    def run(self):
        self.env.note_dependency(__file__)

        items = nodes.bullet_list(classes=['elbe-website-version-list'])

        for version in _docs_versions(self.config):
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


def _write_sitemap(app, exception):
    if exception is not None:
        return

    builder = app.builder

    if builder.format != 'html':
        return

    baseurl = builder.config.html_baseurl
    docs_directory = _docs_directory(builder.config)
    docs_versions = _docs_versions(builder.config)

    f = open(os.path.join(app.outdir, 'sitemap.xml'), 'w')
    sitemap = xml.sax.saxutils.XMLGenerator(f, encoding='utf-8')
    sitemap.startDocument()
    sitemap.startPrefixMapping('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    sitemap.startElementNS(('http://www.sitemaps.org/schemas/sitemap/0.9', 'urlset'), None, {})

    priority = 1.0
    _inventory_sitemap(sitemap, baseurl, os.path.join(app.outdir, 'objects.inv'), priority=priority)

    for version in docs_versions:
        _inventory_sitemap(sitemap, _versioned_doc_directory(version),
                           os.path.join(docs_directory, f'v{version}', 'objects.inv'),
                           priority=priority)
        priority *= 0.8

    sitemap.ignorableWhitespace('\n')
    sitemap.endElement('urlset')
    sitemap.endPrefixMapping('urlset')
    sitemap.endDocument()


def _inventory_sitemap(sitemap, baseurl, inventory_path, priority):
    with open(inventory_path, 'rb') as f:
        inventory = InventoryFile.load(f, baseurl, None)

    for doc in inventory.get('std:doc', {}).values():
        sitemap.ignorableWhitespace('\n  ')
        sitemap.startElement('url', {})

        sitemap.ignorableWhitespace('\n    ')
        sitemap.startElement('loc', {})
        sitemap.characters(doc.uri)
        sitemap.endElement('loc')

        sitemap.ignorableWhitespace('\n    ')
        sitemap.startElement('priority', {})
        sitemap.characters('{:.6f}'.format(priority))
        sitemap.endElement('priority')

        sitemap.ignorableWhitespace('\n  ')
        sitemap.endElement('url')


def setup(app):
    app.add_config_value('elbedocoverview_docs_directory', None, 'env', str)
    app.add_directive('elbedocoverview', _ElbeDocOverview)
    app.add_directive('elbe-container-with-titles', _ElbeContainerWithTitles)
    app.add_node(section_level, html=(visit_section_level_node, depart_section_level_node))
    app.connect('config-inited', _config_inited)
    app.connect('build-finished', _write_sitemap)
    app.add_css_file('elbe-website.css')

    return {
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
