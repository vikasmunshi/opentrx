#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python implementation of Unix Daemon
"""
import atexit
import os
import pwd
import stat
import sys
import time
from abc import ABCMeta, abstractmethod

from xlib.loggerconfig import LoggerConfiguration

__version__ = '0.1'


class Daemon(object, metaclass=ABCMeta):
    """
    class daemon
    """

    @abstractmethod
    def preworker(self, args: dict) -> None:
        pass

    @abstractmethod
    def worker(self, args: dict) -> None:
        pass

    @abstractmethod
    def postworker(self, args: dict) -> None:
        pass

    def __init__(self):
        self.umask = int('0133', 8)
        self.classname = self.__class__.__name__
        self.basedir = os.path.dirname(os.path.abspath(__file__))
        basedirstats = os.stat(self.basedir)
        self.uid, self.gid = basedirstats.st_uid, basedirstats.st_gid
        sysuser = os.getuid()
        if sysuser not in (0, self.uid):
            self.basedir = os.path.expanduser('~')
            self.uid, self.gid = sysuser, os.getgid()
        self.username = pwd.getpwuid((self.uid)).pw_name
        self.logfile = os.path.join(self.basedir, 'stdout_' + self.classname + '.txt')
        self.errfile = os.path.join(self.basedir, 'stderr_' + self.classname + '.txt')
        self.pidfile = os.path.join(self.basedir, 'pid_' + self.classname + '.txt')
        self.iamdaemon = None

    def __fork__(self) -> bool:
        return os.fork() == 0

    def __doatexit__(self) -> None:
        try:
            os.remove(self.pidfile)
        except Exception as e:
            self.logger.exception(e)

    def __daemonize__(self) -> bool:
        for file in (self.basedir, self.logfile, self.errfile):
            filestat = os.stat(file) if os.path.exists(file) else None
            assert filestat is None \
                   or (filestat.st_uid == self.uid and stat.filemode(filestat.st_mode)[1:3] == 'rw'), \
                'file ownership or permissions not correct\n file {0}\n owner {1}\n mode {2}\n'.format(
                    file,
                    pwd.getpwuid(filestat.st_uid).pw_name,
                    stat.filemode(filestat.st_mode)
                )
        if self.__fork__():
            os.setsid()
            if self.__fork__():
                os.chdir(self.basedir)
                os.setgid(self.gid)
                os.setuid(self.uid)
                sys.stdout.flush()
                sys.stderr.flush()
                for fd in range(0, os.sysconf('SC_OPEN_MAX')):
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                os.umask(self.umask)
                self.logger, sys.stdout, sys.stderr = LoggerConfiguration(loggername=self.classname,
                                                                          logfile=self.logfile,
                                                                          errfile=self.errfile).getfilehandles
                try:
                    with open(self.pidfile, 'x') as pidfile:
                        pidfile.write(str(os.getpid()) + '\n')
                except FileExistsError:
                    self.iamdaemon = False
                else:
                    self.iamdaemon = True
                    atexit.register(self.__doatexit__)
                return self.iamdaemon
            else:
                os._exit(0)
        else:
            os._exit(0)

    @property
    def umask(self) -> int:
        return self.__umask__

    @umask.setter
    def umask(self, mask) -> None:
        assert isinstance(mask, int)
        self.__umask__ = mask

    @property
    def status(self) -> int:
        try:
            with open(self.pidfile, 'r') as pidfile:
                pid = int(pidfile.read())
            os.kill(pid, 0)
        except (FileNotFoundError, OSError):
            return 0
        else:
            return pid

    def start(self, args: tuple = (), preworkerargs: dict = None, workerargs: dict = None,
              postworkerargs: dict = None) -> None:
        if self.status == 0:
            if self.__fork__():
                if self.__daemonize__():
                    try:
                        self.preworker(preworkerargs)
                        try:
                            self.worker(workerargs)
                        except KeyboardInterrupt:
                            self.logger.info('worker recieved KeyboardInterrupt')
                        self.postworker(postworkerargs)
                    except Exception as e:
                        self.logger.exception(e)
                    if 'donotexit' not in args: sys.exit(0)
            else:
                time.sleep(0.1)

    def stop(self, attempts: int = 10) -> int:
        pid = self.status
        while pid != 0 and attempts > 0:
            try:
                os.kill(pid, 2)  # signal.SIGINT
            except:
                pass
            time.sleep(0.1)
            pid = self.status
            attempts -= 1
        return pid
