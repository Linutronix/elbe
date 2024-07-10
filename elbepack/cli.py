# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

_decorator_argparse_attr = '__' + __name__ + '.decorator_argparse'


def add_argument(*args, **kwargs):
    """
    Record calls to :py:meth:`argparse.ArgumentParser.add_argument` to later be
    applied by :py:func:`add_arguments_from_decorated_function`.
    """
    def decorator(f):
        if not hasattr(f, _decorator_argparse_attr):
            setattr(f, _decorator_argparse_attr, [])

        attr = getattr(f, _decorator_argparse_attr)
        # Decorators are evaluated inner-first, which means the bottom decorator is first.
        # Invert the list to provide top-first behavior.
        attr.insert(0, (args, kwargs))
        return f

    return decorator


def add_arguments_from_decorated_function(parser, f):
    """
    Apply calls to :py:meth:`argparse.ArgumentParser.add_argument` recorded by
    :py:func:`add_argument`.
    """
    for args, kwargs in getattr(f, _decorator_argparse_attr, []):
        parser.add_argument(*args, **kwargs)
