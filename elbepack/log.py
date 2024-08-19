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
context_fmt = logging.Formatter('%(context)s%(message)s')
msgonly_fmt = logging.Formatter('%(message)s')
log = logging.getLogger('log')
soap = logging.getLogger('soap')
report = logging.getLogger('report')
validation = logging.getLogger('validation')


class LoggingQueue(collections.deque):
    def __init__(self):
        super().__init__(maxlen=1024)
        self._max_level = logging.NOTSET

    def note_level(self, level):
        if level > self._max_level:
            self._max_level = level

    def reset_level(self):
        self._max_level = logging.NOTSET

    def max_level(self):
        return self._max_level


_queues = {}


class QHandler(logging.Handler):
    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if target not in _queues:
            _queues[target] = LoggingQueue()
        self.Q = _queues[target]

    def emit(self, record):
        self.Q.append(self.format(record))
        self.Q.note_level(record.levelno)


def read_loggingQ(proj):
    try:
        return _queues[proj].popleft()
    except (IndexError, KeyError):
        return ''


def read_maxlevel(proj):
    try:
        return _queues[proj].max_level()
    except (IndexError, KeyError):
        return logging.NOTSET


def reset_level(proj):
    try:
        _queues[proj].reset_level()
    except (IndexError, KeyError):
        pass


class ThreadFilter(logging.Filter):

    def __init__(self, allowed, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed = {a.name for a in allowed}
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


class _NullStream:
    def write(self, data):
        pass


def add_stream_handlers(streams):

    for stream in streams:
        if stream == os.devnull:
            stream = _NullStream()

        out = logging.StreamHandler(stream)
        out.addFilter(ThreadFilter([root, log, report, validation, soap])),
        out.setFormatter(context_fmt)
        yield out


def add_project_handlers(projects):

    for proj in projects:
        validation_handler = logging.FileHandler(os.path.join(proj, 'validation.txt'))
        report_handler = logging.FileHandler(os.path.join(proj, 'elbe-report.txt'))
        log_handler = logging.FileHandler(os.path.join(proj, 'log.txt'))
        echo_handler = QHandler(proj)
        soap_handler = QHandler(proj)

        validation_handler.addFilter(ThreadFilter([validation]))
        report_handler.addFilter(ThreadFilter([report]))
        log_handler.addFilter(ThreadFilter([root, log, report, validation]))
        echo_handler.addFilter(ThreadFilter([root, report, validation]))
        soap_handler.addFilter(ThreadFilter([soap]))

        validation_handler.setFormatter(msgonly_fmt)
        report_handler.setFormatter(msgonly_fmt)
        log_handler.setFormatter(context_fmt)
        echo_handler.setFormatter(context_fmt)
        soap_handler.setFormatter(context_fmt)

        yield from [validation_handler, report_handler, log_handler, echo_handler, soap_handler]


_logging_methods = {
    'streams': add_stream_handlers,
    'projects': add_project_handlers,
}


@contextmanager
def elbe_logging(*args, **kwargs):
    cleanup = open_logging(*args, **kwargs)
    try:
        yield
    finally:
        cleanup()


def open_logging(**targets):
    root.setLevel(logging.DEBUG)

    handlers = []

    for key, call in _logging_methods.items():
        if key in targets:
            destinations = targets[key]
            if not isinstance(destinations, list):
                destinations = [destinations]

            for h in call(destinations):
                handlers.append(h)
                root.addHandler(h)

    def _cleanup():
        for h in handlers:
            root.removeHandler(h)
            h.close()

    return _cleanup


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
