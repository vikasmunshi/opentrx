#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP Request Handler
"""
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler, HTTPStatus
from socketserver import ThreadingMixIn

from xlib.loggerconfig import LoggerConfiguration

__version__ = '0.1'
RESPONSESTUB = """<html><body><h1>ana</h1></body></html>""".encode()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class RequestHandler(BaseHTTPRequestHandler):
    server_version = 'ListnerRequestHandler {} BaseHTTPRequestHandler {}'.format(__version__,
                                                                                 BaseHTTPRequestHandler.server_version)

    @classmethod
    def setlogger(cls, basedir: str) -> None:
        logfile = os.path.join(basedir, 'stdout_' + cls.__name__ + '.txt')
        errfile = os.path.join(basedir, 'stderr_' + cls.__name__ + '.txt')
        cls.logger, sys.stdout, sys.stderr = LoggerConfiguration(loggername=cls.__name__,
                                                                 logfile=logfile,
                                                                 errfile=errfile).getfilehandles

    def log_request(self, code: HTTPStatus = None, size: int = None) -> None:
        self.logger.info(
            '{} {} {} {} "{}" {} {}'.format(self.address_string(), '-', '-', self.log_date_time_string(),
                                            self.requestline,
                                            code.value if isinstance(code, HTTPStatus) else '-',
                                            size or ' - ')
        )

    def log_error(self, formatstring, *args) -> None:
        self.logger.error('%s - - [%s] %s' % (self.address_string(), self.log_date_time_string(), formatstring % args))

    def log_message(self, formatstring, *args) -> None:
        """
            "%h %l %u %t \"%r\" %>s %b"
            "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-agent}i\""
            %h	Remote hostname
            %l	Remote logname (from identd, if supplied)
            %u	Remote user if the request was authenticated
            %t	Time the request was received, in the format [18/Sep/2011:19:18:28 -0400]
            %r	First line of request
            %>s	Status. Use %>s for the final status.
            %b	Size of response in bytes, excluding HTTP headers.
            %{VARNAME}i	The contents of VARNAME: header line(s) in the request sent to the server.
        """
        self.logger.info('%s - - [%s] %s' % (self.address_string(), self.log_date_time_string(), formatstring % args))

    def stub(self) -> None:
        status = HTTPStatus.OK
        result = RESPONSESTUB
        self.send_response(status)
        self.send_header("Content-type", 'text/html')
        self.send_header("Last-Modified", 'Sun, 24 Jan 2016 21:19:20 GMT')
        self.end_headers()
        self.wfile.write(result)
        self.log_request(status, len(result))
        return

    def do_GET(self) -> None:
        self.stub()
        return

    def do_POST(self) -> None:
        self.stub()
        pass
