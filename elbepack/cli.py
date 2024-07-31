# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2024 Linutronix GmbH

import dataclasses
import inspect
import os.path
import traceback
import types
import typing


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


def add_argument_to_parser_or_function(parser_or_func, *args, **kwargs):
    """
    Add arguments either to an :py:meth:`argparse.ArgumentParser` and similar objects,
    or to a decoracted function, the same as :py:meth:`add_argument`.
    """
    if hasattr(parser_or_func, 'add_argument'):
        return parser_or_func.add_argument(*args, **kwargs)

    elif callable(parser_or_func):
        return add_argument(*args, **kwargs)(parser_or_func)

    else:
        raise ValueError(parser_or_func)


def add_arguments_from_decorated_function(parser, f):
    """
    Apply calls to :py:meth:`argparse.ArgumentParser.add_argument` recorded by
    :py:func:`add_argument`.
    """
    for args, kwargs in getattr(f, _decorator_argparse_attr, []):
        parser.add_argument(*args, **kwargs)


@dataclasses.dataclass
class _CliDetails:
    message: str
    exitcode: int


_cli_details_attr_name = __name__ + '.__cli_details'


def with_cli_details(exc, exitcode=1, message=None):
    """
    Extend a given exception with additional information which will be used when this
    exception is stopping the process.
    """
    setattr(exc, _cli_details_attr_name, _CliDetails(
        message=message,
        exitcode=exitcode,
    ))
    return exc


def _get_cli_details(exc):
    return getattr(exc, _cli_details_attr_name, None)


class CliError(RuntimeError):
    """
    Exception type for errors not attached to an existing exception.
    """
    def __init__(self, exitcode=1, message=None):
        with_cli_details(self, exitcode=exitcode, message=message)
        self.args = (message,)


def _last_frame_in_package(tb, package):
    frame = tb.tb_frame

    while tb.tb_next is not None:
        tb = tb.tb_next
        mod = inspect.getmodule(tb)
        if mod is None:
            continue
        name = mod.__spec__.name
        if name and (name == package or name.startswith(package + '.')):
            frame = tb.tb_frame

    return frame


class _SupportsStrWrite(typing.Protocol):
    def write(self, value: str): ...


def format_exception(exc: Exception,
                     output: _SupportsStrWrite,
                     verbose: bool,
                     base_module: types.ModuleType):
    """
    Format an exception `exc` for user consumption to `output`.
    If `verbose` is True print the full stacktrace, otherwise only provide the
    message and source location.
    The source location is limited to the stack frames within `base_module`.
    """
    tb = exc.__traceback__
    cli_details = _get_cli_details(exc)

    if cli_details is not None and cli_details.message is not None:
        print(cli_details.message, file=output)

    if verbose:
        traceback.print_exception(None, value=exc, tb=tb, file=output)
    else:
        frame = _last_frame_in_package(tb, base_module.__name__)
        filename = os.path.normpath(frame.f_code.co_filename)
        if isinstance(exc, CliError):
            print(f'{filename}:{frame.f_lineno}', file=output)
        else:
            print(f'{filename}:{frame.f_lineno}: '
                  f'{type(exc).__name__}: {exc}', file=output)

    return cli_details.exitcode if cli_details is not None else 1
