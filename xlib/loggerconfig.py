#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Logger configuration
"""
import logging
import logging.handlers

__version__ = '0.1'


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger: logging.Logger, loglevel: int):
        self.logger = logger
        self.loglevel = loglevel
        self.linebuf = ''

    def write(self, buf: str) -> None:
        for line in buf.rstrip().splitlines():
            self.logger.log(self.loglevel, line.rstrip())

    def flush(self) -> None:
        pass

    def filter(self, logrecord: logging.LogRecord) -> bool:
        return logrecord.levelno <= self.loglevel


class LoggerConfiguration(object):
    """
    Helper object that sets up logging handlers
    """

    def __init__(self, loggername: str, logfile: str, errfile: str,
                 loglevel: int = logging.INFO, errlevel: int = logging.ERROR):
        self.__logger__ = logging.getLogger(loggername)
        self.__logger__.setLevel(logging.INFO)
        self.__stdout__ = StreamToLogger(self.__logger__, loglevel)
        self.__stderr__ = StreamToLogger(self.__logger__, errlevel)
        handlers = dict([(h.handlerid, h) for h in self.__logger__.handlers if hasattr(h, 'handlerid')])
        loghandlerid = self.__logger__.name + '://' + logfile + ':' + str(loglevel)
        errhandlerid = self.__logger__.name + '://' + errfile + ':' + str(errlevel)
        if loghandlerid not in handlers:
            handler = logging.handlers.TimedRotatingFileHandler(logfile, when='midnight')
            handler.setLevel(loglevel)
            handler.handlerid = loghandlerid
            handler.addFilter(self.__stdout__.filter)
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s|%(levelname)s|%(process)d|%(threadName)s|%(module)s|%(funcName)s|%(message)s'))
            self.__logger__.addHandler(handler)
        if errhandlerid not in handlers:
            handler = logging.handlers.TimedRotatingFileHandler(errfile, when='midnight')
            handler.setLevel(errlevel)
            handler.handlerid = errhandlerid
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s|%(levelname)s|%(process)d|%(threadName)s|%(module)s|%(funcName)s|%(message)s'))
            self.__logger__.addHandler(handler)

    @property
    def logger(self) -> logging.Logger:
        return self.__logger__

    @property
    def stdout(self) -> StreamToLogger:
        return self.__stdout__

    @property
    def stderr(self) -> StreamToLogger:
        return self.__stderr__

    @property
    def getfilehandles(self) -> (logging.Logger, StreamToLogger, StreamToLogger):
        return self.__logger__, self.__stdout__, self.__stderr__
