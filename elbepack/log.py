# ELBE - Debian Based Embedded Rootfilesystem Builder
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2019 Linutronix GmbH


import collections
import logging
import os
import re
import threading
from contextlib import contextmanager


root = logging.getLogger()
root.setLevel(logging.DEBUG)
local = threading.local()
context_fmt = logging.Formatter('%(context)s%(message)s')
msgonly_fmt = logging.Formatter('%(message)s')
log = logging.getLogger('log')
soap = logging.getLogger('soap')


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

    @classmethod
    def reset_level(cls, target):
        try:
            cls.queues[target].max_level = logging.NOTSET
        except (IndexError, KeyError):
            pass


def read_loggingQ(proj):
    return QHandler.pop(proj)


def read_maxlevel(proj):
    return QHandler.max_level(proj)


def reset_level(proj):
    QHandler.reset_level(proj)


class ThreadFilter(logging.Filter):

    def __init__(self, allowed, *args, **kwargs):
        super(ThreadFilter, self).__init__(*args, **kwargs)
        self.allowed = allowed
        self.thread = threading.current_thread().ident

    def filter(self, record):
        if hasattr(record, '_thread'):
            # Hack to fake logging for another thread
            thread = record._thread
        else:
            thread = record.thread
        retval = record.name in self.allowed and thread == self.thread
        if retval and not hasattr(record, 'context'):
            record.context = f'[{record.levelname}]'
        return retval


def add_stream_handlers(streams):

    for stream in streams:
        out = logging.StreamHandler(stream)
        out.addFilter(ThreadFilter(['root',
                                    'log',
                                    'report',
                                    'validation',
                                    'soap']))
        out.setFormatter(context_fmt)
        yield out


def add_project_handlers(projects):

    for proj in projects:
        validation = logging.FileHandler(os.path.join(proj, 'validation.txt'))
        report = logging.FileHandler(os.path.join(proj, 'elbe-report.txt'))
        log = logging.FileHandler(os.path.join(proj, 'log.txt'))
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

        yield from [validation, report, log, echo, soap]


_logging_methods = {
    'streams': add_stream_handlers,
    'projects': add_project_handlers,
}


@contextmanager
def elbe_logging(*args, **kwargs):
    try:
        open_logging(*args, **kwargs)
        yield
    finally:
        close_logging()


def open_logging(**targets):

    close_logging()

    for key, call in _logging_methods.items():
        if key in targets:
            destinations = targets[key]
            if not isinstance(destinations, list):
                destinations = [destinations]

            for h in call(destinations):
                local.handlers.append(h)
                root.addHandler(h)


def close_logging():
    if hasattr(local, 'handlers'):
        for h in local.handlers:
            root.removeHandler(h)
            h.close()
    local.handlers = []


class AsyncLogging(threading.Thread):

    def __init__(self, atmost):
        super().__init__(daemon=True)
        self.lines = []
        self.atmost = atmost
        self.read_fd, self.write_fd = os.pipe()
        calling_thread = threading.current_thread().ident
        extra = {'_thread': calling_thread}
        extra['context'] = ''
        self.stream = logging.LoggerAdapter(soap, extra)
        self.block = logging.LoggerAdapter(log, extra)

    def run(self):
        try:
            self.__run()
        finally:
            os.close(self.read_fd)

    def shutdown(self):
        os.close(self.write_fd)

    def __run(self):
        rest = ''

        while True:

            buf = os.read(self.read_fd, self.atmost).decode('utf-8', errors='replace')

            # Pipe broke
            if not buf:
                break

            buf = rest + buf
            cnt = 0
            j = 0

            # Line buffering
            for i in range(len(buf)):
                if buf[i] == '\n':
                    self.lines.append(buf[j:i])
                    cnt += 1
                    j = i + 1

            # Log the line now for echo back
            if cnt:
                logbuf = '\n'.join(self.lines[-cnt:])

                # filter out ansi sequences.
                logbuf = re.sub('\u001b[.*?[@-~(=]', '', logbuf)
                logbuf = re.sub('\u0008', '', logbuf)

                self.stream.info(logbuf)

            # Keep rest for next line buffering
            rest = buf[j:]

        if self.lines:
            self.lines[-1] += rest
            self.block.info('\n'.join(self.lines))


def async_logging(atmost=4096):
    t = AsyncLogging(atmost)
    t.start()
    return t


@contextmanager
def async_logging_ctx(*args, **kwargs):
    t = async_logging(*args, **kwargs)
    try:
        yield t.write_fd
    finally:
        t.shutdown()
        t.join()
