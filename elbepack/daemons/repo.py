# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import logging
import mimetypes
import os
import wsgiref.util


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# taken from wsgiref examples
def _app(environ, respond):
    # Get the file name and MIME type
    fn = environ['PATH_INFO']
    mime_type = mimetypes.guess_type(fn)[0] or 'application/octet-stream'

    # Return 200 OK if file exists, otherwise 404 Not Found
    logger.warn('Serving as %s: "%s"', mime_type, fn)
    if os.path.exists(fn):
        respond('200 OK', [('Content-Type', mime_type)])
        return wsgiref.util.FileWrapper(open(fn, 'rb'))
    else:
        respond('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'not found']


def get_app():
    return _app
