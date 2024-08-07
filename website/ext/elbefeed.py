# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import datetime
import os


def _date_from_pagename(pagename):
    b = os.path.basename(pagename)
    return datetime.date.fromisoformat(b[:10])


def _html_page_context(app, pagename, templatename, context, doctree):
    if pagename.startswith('news/') and pagename != 'news/index':
        context['meta']['date'] = _date_from_pagename(pagename)
        return 'news.html'


def setup(app):
    app.connect('html-page-context', _html_page_context)

    return {
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
