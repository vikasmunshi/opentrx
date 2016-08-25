#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import abc
import atexit
import os
import sys
from os.path import abspath, dirname, exists, expanduser, isdir, join
from pwd import getpwuid
from stat import filemode
from time import sleep

from xlib.loggerconfig import LoggerConfiguration

__version__ = '0.1'


class Daemon(object, metaclass=abc.ABCMeta):
    """
    Daemon is an abstract class implementation of well-behaved Unix daemon specification of PEP 3143.
    It implements the double fork method to 'daemonize'.
    Abstract methods preworker(), worker(), and postworker() must be overridden in the derived class.
    Invocation of the start() method results in:
        if not already running as daemon,
            current process is forked, code execution continues in the parent and child process is daemonised;
            stdout and stdrr are mapped to files in basedir/../log/ dir;
            current dir is changed to basedir/../var/ dir
            if started as root (uid 0), the process owner is switched to file owner
            the three methods preworker(), worker(), and postworker() of the derived class are invoked in order
            KeyboardInterrupt is trapped while executing worker()
    Invocation of the stop() method results in sending SIGINT signal to (any) running daemon instance
    status() returns 0 if no daemon is running, else the PID of the running daemon process
    Refer https://www.python.org/dev/peps/pep-3143/
    TODO: Trap other interrupts
    """

    def __init__(self):
        self.__uid__ = None
        self.__gid__ = None
        self.__username__ = None
        self.__logfile__ = None
        self.__errfile__ = None
        self.__pidfile__ = None
        self.__umask__ = None
        self.__basedir__ = None
        self.__umask__ = None

    @abc.abstractmethod
    def preworker(self, args: dict) -> None:
        """
        Override this; code to be executed before executing worker
        :param args: dictionary of arguments
        :return: None
        """
        pass

    @abc.abstractmethod
    def worker(self, args: dict) -> None:
        """
        Override this with worker code; expect this to include code that runs forever (not necessary)
        Trap SIGINT to manage code termination
        :param args: dictionary of arguments
        :return: None
        """
        pass

    @abc.abstractmethod
    def postworker(self, args: dict) -> None:
        """
        Override this; code to be executed after worker terminates
        :param args: dictionary of arguments
        :return: None
        """
        pass

    def status(self) -> int:
        """
        Check if pidfile exists, read the pid and check if it is still running
        Else only check if the pid is still running
        :return: PID of any running daemon instance, 0 if no daemon instance is running
        """
        try:
            with open(self.pidfile, 'r') as pidfile:
                pid = int(pidfile.read())
            os.kill(pid, 0)
        except (FileNotFoundError, OSError):
            return 0
        else:
            return pid

    def stop(self, attempts: int = 10) -> int:
        """
        Get status and send SIGINT to any running PID
        :param attempts: number of times to try to send SIGINT to any running PID, default 10
        :return: PID of any running daemon instance, 0 if no daemon instance is running
        """
        pid = self.status()
        while not (pid == 0 or attempts < 0):
            try:
                os.kill(pid, 2)  # signal.SIGINT
            except OSError:
                pass
            sleep(0.1)
            pid = self.status()
            attempts -= 1
        return pid

    def start(self, preworkerargs: dict = (), workerargs: dict = (), postworkerargs: dict = ()) -> None:
        """
        Deamonise the process and execute preworker(), worker(), and postworker() in order
        Code execution will continue in the calling process
        Trap SIGINT while executing worker()
        :param preworkerargs: optional dictionary to pass to preworker()
        :param workerargs: optional dictionary to pass to worker()
        :param postworkerargs: optional dictionary to pass to postworker()
        :return: None
        """
        if self.status() == 0:
            for target in (self.logdir, self.vardir, self.logfile, self.errfile):
                filestat = os.stat(target) if exists(target) else None
                assert filestat is None or (
                    filestat.st_uid == self.uid and filemode(filestat.st_mode)[1:3] == 'rw'), \
                    'file ownership or permissions not correct\n file {0}\n owner {1}\n mode {2}\n'.format(
                        target, getpwuid(filestat.st_uid).pw_name, filestat.st_uid, filemode(filestat.st_mode))
            if os.fork() == 0:
                if self.__daemonize__:
                    try:
                        self.preworker(preworkerargs)
                        try:
                            self.worker(workerargs)
                        except KeyboardInterrupt:
                            self.logger.info('worker recieved KeyboardInterrupt')
                        self.postworker(postworkerargs)
                    except Exception as e:
                        self.logger.exception(e)
                    sys.exit(0)
            else:
                sleep(0.1)

    @property
    def __daemonize__(self) -> bool:
        """
        Daemonise the current process using double fork method; kill intermediate child processes
        :return: True if pid written to file for daemon process, else False
        """
        if os.fork() == 0:
            os.setsid()
            if os.fork() == 0:
                sys.stdout.flush()
                sys.stderr.flush()
                os.setgid(self.gid)
                os.setuid(self.uid)
                os.chdir(self.vardir)
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
                    return False
                else:
                    atexit.register(self.__doatexit__)
                    return True
            else:
                # noinspection PyProtectedMember
                os._exit(0)
        else:
            # noinspection PyProtectedMember
            os._exit(0)

    def __doatexit__(self) -> None:
        """
        Remove the pid file
        :return: None
        """
        try:
            os.remove(self.pidfile)
        except Exception as e:
            self.logger.exception(e)

    @property
    def classname(self) -> str:
        return self.__class__.__name__

    @property
    def uid(self) -> int:
        if self.__uid__ is None:
            osuid = os.getuid()
            self.__uid__ = os.stat(__file__).st_uid if osuid == 0 else osuid
        return self.__uid__

    @property
    def gid(self) -> int:
        if self.__gid__ is None:
            self.__gid__ = os.stat(__file__).st_gid if os.getuid() == 0 else os.getgid()
        return self.__gid__

    @property
    def username(self) -> str:
        if self.__username__ is None:
            self.__username__ = getpwuid(self.uid).pw_name
        return self.__username__

    @property
    def logfile(self) -> str:
        if self.__logfile__ is None:
            self.__logfile__ = join(self.logdir, 'stdout_' + self.classname + '.txt')
        return self.__logfile__

    @property
    def errfile(self) -> str:
        if self.__errfile__ is None:
            self.__errfile__ = join(self.logdir, 'stderr_' + self.classname + '.txt')
        return self.__errfile__

    @property
    def pidfile(self) -> str:
        if self.__pidfile__ is None:
            self.__pidfile__ = abspath(join(join(self.logdir, '../log'), 'pid_' + self.classname + '.txt'))
        return self.__pidfile__

    @property
    def logdir(self) -> str:
        return abspath(join(self.basedir, '../log/'))

    @property
    def vardir(self) -> str:
        return abspath(join(self.basedir, '../var/'))

    @property
    def umask(self) -> int:
        if self.__umask__ is None:
            self.__umask__ = int('0133', 8)
        return self.__umask__

    @umask.setter
    def umask(self, mask: int) -> None:
        assert isinstance(mask, int)
        self.__umask__ = mask

    @property
    def basedir(self) -> str:
        if self.__basedir__ is None:
            codebasedir = dirname(abspath(__file__))
            if os.getuid() in (0, os.stat(codebasedir).st_uid):
                self.__basedir__ = codebasedir
            else:
                self.__basedir__ = expanduser('~')
        return self.__basedir__

    @basedir.setter
    def basedir(self, directory: str) -> None:
        assert isinstance(directory, str)
        assert exists(directory)
        assert isdir(directory)
        self.__basedir__ = directory
