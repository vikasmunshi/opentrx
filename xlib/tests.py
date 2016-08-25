#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for Python implementation of Unix Daemon
"""
import http.client
import ssl
import time
from json import loads

from xlib.listener import Listener

if __name__ == '__main__':
    print('ana')

    listner = Listener()
    listner.host = 'localhost'
    listner.start()
    print(listner.status())
    listner = None
    time.sleep(2)

    try:
        with open('../var/host.txt', 'r') as hostfile:
            url, host, port = loads(hostfile.readline())
        conn = http.client.HTTPSConnection(host=host, port=port,
                                           context=ssl.create_default_context(cafile='../var/cert.pem'))
        for url in ('/', '/ana'):
            st = time.time()
            conn.request(method='GET', url=url)
            res = conn.getresponse()
            print(url, res.status, res.reason, res.read())
            print(time.time() - st)
    finally:
        Listener().stop()

    print('ana')
