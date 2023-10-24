#! /usr/bin/env python3

import argparse
import socket
import os
import ssl
import threading
import time
import sys

LISTEN = 5

# speed limiter

# REDIRECT_LOOP_SPEEP = 0.01
SPEED_LIMIT_SLEEP = 0.05 # seconds

# certificates

HERE = os.path.dirname(os.path.realpath(__file__))
SSL_KEYFILE  = os.path.join(HERE, 'certs', 'private.key')
SSL_CERTFILE = os.path.join(HERE, 'certs', 'certificate.crt')

def redirect_traffic(con, addr, server_port, speed_limit):
    try:
        redirect_traffic2(con, addr, server_port, speed_limit)
    finally:

        try:
            con.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        con.close()

def redirect_traffic2(client, client_addr, server_port, speed_limit):
    speed_limit *= 1024 * 1024
    download_chunk = int(speed_limit * SPEED_LIMIT_SLEEP)
    upload_chunk = int(speed_limit * SPEED_LIMIT_SLEEP)

    client.setblocking(False)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect(('localhost', server_port))
    server.setblocking(False)

    next_upload = 0
    next_download = 0

    while True:
        
        if time.time() >= next_download:
            try:
                data = client.recv(download_chunk)
            except BlockingIOError:
                pass
            except ssl.SSLWantReadError:
                pass
            else:
                next_download = time.time() + SPEED_LIMIT_SLEEP * (len(data) / download_chunk)

                server.setblocking(True)
                server.sendall(data)
                server.setblocking(False)

        if time.time() >= next_upload:
            try:
                data = server.recv(upload_chunk)
            except BlockingIOError:
                pass
            else:
                if len(data) == 0:
                    break

                next_upload = time.time() + SPEED_LIMIT_SLEEP * (len(data) / upload_chunk)

                client.setblocking(True)
                client.sendall(data)
                client.setblocking(False)
                time.sleep(SPEED_LIMIT_SLEEP)
        
        # time.sleep(REDIRECT_LOOP_SPEEP)

    print('done')

def main_connection_accepter(sock, server_port, speed_limit):
    while True:
        try:
            while True:
                conn, addr = sock.accept()
                threading.Thread(target=redirect_traffic, args=[conn, addr, server_port, speed_limit]).start()
        except:
            pass

def main(server_port, wrapper_port, speed_limit):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock = ssl.wrap_socket(
        sock, 
        keyfile=SSL_KEYFILE,
        certfile=SSL_CERTFILE,
        server_side=True,
    )

    sock.bind(('', wrapper_port))
    sock.listen(LISTEN)

    threading.Thread(target=main_connection_accepter, args=[sock, server_port, speed_limit]).start()

    try:
        while True:
            time.sleep(12345)
    except KeyboardInterrupt:
        sys.exit(69)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ssl wrapper for non-ssl servers')
    parser.add_argument('server_port', type=int, help='port of non-ssl server')
    parser.add_argument('wrapper_port', type=int, help='port for the ssl wrapper')
    parser.add_argument('speed_limit', type=float, help='upload and download speeds will each be limited to this number (MiB)')
    args = parser.parse_args()

    main(args.server_port, args.wrapper_port, args.speed_limit)
