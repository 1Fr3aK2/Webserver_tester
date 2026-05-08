#!/usr/bin/env python3
"""Testar comportamento do servidor quando CGI é invocado com recursos esgotados"""
import socket
import time

def test_cgi_concurrency(host, port, path, n=200):
    """Enviar muitos requests CGI simultâneos para esgotar fds"""
    sockets = []
    req = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: keep-alive\r\n\r\n"
    print(f"[*] Enviando {n} requests para {path}")
    for i in range(n):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.send(req.encode())
            sockets.append(s)
        except Exception as e:
            print(f"    Falhou em {i}: {e}")
            break
    time.sleep(2)
    for s in sockets:
        try:
            data = s.recv(1024)
            if not data:
                print("    ⚠️ Servidor fechou ligação inesperadamente")
        except:
            pass
        s.close()
    print("[*] Teste concluído — verificar se servidor ainda responde")

test_cgi_concurrency("localhost", 8080, "/cgi-bin/test.php")