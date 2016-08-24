#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSL listener
"""
import random
import socket
from _ssl import PROTOCOL_TLSv1 as PROTOCOL_TLS
from base64 import b64encode
from json import dumps
from os import urandom, unlink
from ssl import SSLContext
from tempfile import NamedTemporaryFile

from OpenSSL import crypto

from xlib.daemon import Daemon
from xlib.requesthandler import ThreadedHTTPServer, RequestHandler

__version__ = '0.1'
CERTFILESTORE = 'cert.pem'
HOSTNAMEFILE = 'host.txt'


class Listener(Daemon):
    encoding = 'utf-8'

    def __init__(self):
        super().__init__()
        self.__certstore__ = None
        self.__host__ = None
        self.__port__ = None
        self.__passphrase__ = None
        self.__sslkey__ = None
        self.__sslcert__ = None

    def preworker(self, args: dict) -> None:
        self.logger.info('started preworker')
        self.initserver()
        self.__certstore__ = NamedTemporaryFile()
        with open(self.__certstore__.name, 'w') as tempcertfile:
            tempcertfile.write(self.__sslkey__ + self.__sslcert__)
            tempcertfile.flush()
            self.logger.info('key written to file ' + self.__certstore__.name)
        self.logger.info('done preworker')

    def postworker(self, args: dict) -> None:
        self.logger.info('started postworker')
        self.__certstore__.close()
        self.logger.info('removed key file ' + self.__certstore__.name)
        for cleanupfile in CERTFILESTORE, HOSTNAMEFILE:
            try:
                unlink(cleanupfile)
                self.logger.info('deleted file ' + cleanupfile)
            except Exception as e:
                self.logger.exception(e)
        self.logger.info('done postworker')

    def worker(self, args: dict) -> None:
        self.logger.info('started worker')
        context = SSLContext(protocol=PROTOCOL_TLS)
        context.load_cert_chain(certfile=self.__certstore__.name, password=self.__passphrase__.decode())
        https_server = ThreadedHTTPServer(self.address, RequestHandlerClass=RequestHandler)
        https_server.RequestHandlerClass.setlogger(self.basedir)
        https_server.socket = context.wrap_socket(https_server.socket, server_side=True)
        try:
            self.logger.info('ready to serve httpd')
            https_server.serve_forever()
        except KeyboardInterrupt as k:
            self.logger.info('httpd recieved KeyboardInterrupt')
            raise k
        except Exception as e:
            self.logger.exception(e)
        finally:
            https_server.server_close()
        self.logger.info('done worker')

    @property
    def address(self) -> (str, int):
        return self.host, self.port

    @address.setter
    def address(self, addr: (str, int)) -> None:
        assert isinstance(addr[0], str)
        assert isinstance(addr[1], int)
        self.host, self.port = addr

    @property
    def host(self) -> str:
        if self.__host__ is None:
            self.__host__ = socket.getfqdn()
        return self.__host__

    @host.setter
    def host(self, servername: str) -> None:
        assert isinstance(servername, str)
        self.__host__ = servername

    @property
    def port(self) -> int:
        if self.__port__ is None:
            self.__port__ = random.randint(49152, 65535)
        return self.__port__

    @port.setter
    def port(self, portnumber: int) -> None:
        assert isinstance(portnumber, int)
        assert portnumber >= 49152
        assert portnumber <= 65535
        self.__port__ = portnumber

    @property
    def passphrase(self) -> bytes:
        return self.__passphrase__

    def initserver(self) -> None:
        self.__passphrase__ = b64encode(urandom(128))
        if self.__sslkey__ is None:
            key = crypto.PKey()
            key.generate_key(type=crypto.TYPE_RSA, bits=4096)
            cert = crypto.X509()
            cert.get_subject().C = 'NL'
            cert.get_subject().O = 'opentrx'
            cert.get_subject().OU = self.classname
            cert.get_subject().CN = self.host
            cert.set_serial_number(self.port)
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(365 * 24 * 3600)
            cert.set_issuer(cert.get_subject())
            cert.set_pubkey(key)
            cert.sign(key, 'sha1')
            self.__sslkey__ = crypto.dump_privatekey(type=crypto.FILETYPE_PEM, pkey=key, cipher='aes256',
                                                     passphrase=self.__passphrase__).decode()
            self.__sslcert__ = crypto.dump_certificate(type=crypto.FILETYPE_PEM, cert=cert).decode()
        with open(CERTFILESTORE, 'w') as certfile:
            certfile.write(self.__sslcert__)
            self.logger.info('saved cert in file ' + CERTFILESTORE)
        with open(HOSTNAMEFILE, 'w') as hostfile:
            hostfile.write(dumps(('https://', self.__host__, self.__port__)))
            self.logger.info('saved host info in file ' + HOSTNAMEFILE)
