# ELBE - Debian Based Embedded Rootfilesystem Builder
# Copyright (c) 2019 Olivier Dion <dion@linutronix.de>
#
# SPDX-License-Identifier: GPL-3.0-or-later


import collections
import logging
import os
import select
import threading
from contextlib import contextmanager


root = logging.getLogger()
root.setLevel(logging.DEBUG)
local = threading.local()
context_fmt = logging.Formatter("%(context)s%(message)s")
msgonly_fmt = logging.Formatter("%(message)s")

logging_methods = []


class LoggingQueue(collections.deque):
    def __init__(self):
        super(LoggingQueue, self).__init__(maxlen=1024)
        self.max_level = logging.NOTSET

    def note_level(self, level):
        if level > self.max_level:
            self.max_level = level


class QHandler(logging.Handler):

    queues = {}

    def __init__(self, target, *args, **kwargs):
        super(QHandler, self).__init__(*args, **kwargs)
        if target not in QHandler.queues:
            QHandler.queues[target] = LoggingQueue()
        self.Q = QHandler.queues[target]

    def emit(self, record):
        self.Q.append(self.format(record))
        self.Q.note_level(record.levelno)

    @classmethod
    def pop(cls, target):
        try:
            return cls.queues[target].popleft()
        except (IndexError, KeyError):
            return ''

    @classmethod
    def max_level(cls, target):
        try:
            return cls.queues[target].max_level
        except (IndexError, KeyError):
            return logging.NOTSET


def read_loggingQ(proj):
    return QHandler.pop(proj)


def read_maxlevel(proj):
    return QHandler.max_level(proj)


class ThreadFilter(logging.Filter):

    def __init__(self, allowed, *args, **kwargs):
        super(ThreadFilter, self).__init__(*args, **kwargs)
        self.allowed = allowed
        self.thread = threading.current_thread().ident

    def filter(self, record):
        if hasattr(record, '_thread'):
            thread = record._thread
        else:
            thread = record.thread
        retval = record.name in self.allowed and thread == self.thread
        if retval and not hasattr(record, 'context'):
            record.context = "[%s] " % record.levelname
        return retval


def with_list(func):
    def wrapper(_list):
        if not isinstance(_list, list):
            _list = [_list]
        return func(_list)
    return wrapper


def logging_method(name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for handlers in func(*args, **kwargs):
                for h in handlers:
                    local.handlers.append(h)
                    root.addHandler(h)
        logging_methods.append((name, wrapper))
        return wrapper
    return decorator


@logging_method("streams")
@with_list
def add_stream_handlers(streams):

    for stream in streams:
        out = logging.StreamHandler(stream)
        out.addFilter(ThreadFilter(['root',
                                    'log',
                                    'report',
                                    'validation',
                                    'echo',
                                    'soap']))
        out.setFormatter(context_fmt)
        yield [out]


@logging_method("projects")
@with_list
def add_project_handlers(projects):

    for proj in projects:
        validation = logging.FileHandler(os.path.join(proj, "validation.txt"))
        report = logging.FileHandler(os.path.join(proj, "elbe-report.txt"))
        log = logging.FileHandler(os.path.join(proj, "log.txt"))
        echo = QHandler(proj)
        soap = QHandler(proj)

        validation.addFilter(ThreadFilter(['validation']))
        report.addFilter(ThreadFilter(['report']))
        log.addFilter(ThreadFilter(['root', 'log', 'report', 'validation']))
        echo.addFilter(ThreadFilter(['root', 'report', 'validation']))
        soap.addFilter(ThreadFilter(['soap']))

        validation.setFormatter(msgonly_fmt)
        report.setFormatter(msgonly_fmt)
        log.setFormatter(context_fmt)
        echo.setFormatter(context_fmt)
        soap.setFormatter(context_fmt)

        yield [validation, report, log, echo, soap]


@logging_method("files")
@with_list
def add_file_handlers(files):

    for f in files:
        if f is None:
            out = logging.StreamHandler(os.sys.stdout)
        else:
            out = logging.FileHandler(f)
        out.addFilter(ThreadFilter(['root',
                                    'log',
                                    'report',
                                    'validation',
                                    'echo',
                                    'soap']))
        out.setFormatter(context_fmt)

        yield [out]


@logging_method("projectsQ")
@with_list
def add_projectQ_handlers(projects):

    for proj in projects:
        echo = QHandler(proj)
        soap = QHandler(proj)
        echo.addFilter(ThreadFilter(['root', 'report', 'validation']))
        soap.addFilter(ThreadFilter(['soap']))
        echo.setFormatter(context_fmt)
        soap.setFormatter(context_fmt)
        yield [echo, soap]


@contextmanager
def elbe_logging(*args, **kwargs):
    try:
        open_logging(*args, **kwargs)
        yield
    finally:
        close_logging()


def open_logging(targets):

    close_logging()

    for method in logging_methods:
        key = method[0]
        call = method[1]
        if key in targets:
            call(targets[key])


def close_logging():
    if hasattr(local, "handlers"):
        for h in local.handlers:
            root.removeHandler(h)
    local.handlers = []


class AsyncLogging(object):

    def __init__(self, atmost, stream, block):
        self.lines = []
        self.epoll = select.epoll()
        self.atmost = atmost
        self.fd = None
        calling_thread = threading.current_thread().ident
        extra = {"_thread": calling_thread}
        extra["context"] = ""
        self.stream = logging.LoggerAdapter(stream, extra)
        self.block = logging.LoggerAdapter(block, extra)

    def __call__(self, r, w):
        os.close(w)
        self.epoll.register(r, select.EPOLLIN | select.EPOLLHUP)
        self.fd = r
        try:
            self.run()
        finally:
            os.close(r)

    def run(self):
        alive = True
        rest = ""
        while alive:
            events = self.epoll.poll()
            for _, event in events:
                if event & select.EPOLLIN:
                    rest = self.read(rest)
                if event & select.EPOLLHUP:
                    alive = False

        # Reading rest after pipe hang up
        while True:
            rest = self.read(rest)
            if not rest:
                break

        if self.lines:
            self.lines[-1] += rest
            self.block.info("\n".join(self.lines))

    def read(self, rest):
        buff = rest + os.read(self.fd, self.atmost)
        j = 0
        count = 0
        for i in xrange(len(buff)):
            if buff[i] == '\n':
                self.lines.append(buff[j:i])
                count += 1
                j = i + 1
        if count:
            self.stream.info("\n".join(self.lines[-count:]))
        return buff[j:]


def async_logging(r, w, stream, block, atmost=80):
    t = threading.Thread(target=AsyncLogging(atmost, stream, block),
                         args=(r, w))
    t.daemon = True
    t.start()
