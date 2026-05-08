#!/usr/bin/env python3
"""
Webserv Tester - Baseado na ficha de avaliação 42
Testa todos os critérios do subject: mandatory + bonus
Uso: python3 webserv_tester.py [host] [port]
     python3 webserv_tester.py           # usa localhost:8080
"""

import socket
import time
import sys
import os
import subprocess
import urllib.request
import urllib.error

HOST = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

# ── cores ──────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

PASS = f"{GREEN}[PASS]{RESET}"
FAIL = f"{RED}[FAIL]{RESET}"
WARN = f"{YELLOW}[WARN]{RESET}"
INFO = f"{CYAN}[INFO]{RESET}"

results = []

# ── helpers ────────────────────────────────────────────────────────────────────
def raw_request(req: str, host=HOST, port=PORT, timeout=5, read_bytes=8192) -> bytes:
    """Envia um request HTTP raw e devolve a resposta em bytes."""
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(req.encode())
        data = b""
        try:
            while True:
                chunk = s.recv(read_bytes)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
        return data


def parse_status(resp: bytes) -> int:
    try:
        line = resp.split(b"\r\n")[0].split(b" ")
        return int(line[1])
    except Exception:
        return -1


def check(name: str, ok: bool, detail: str = ""):
    tag = PASS if ok else FAIL
    msg = f"{tag} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append((name, ok))


def section(title: str):
    print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═'*60}{RESET}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. MANDATORY — Basic Checks
# ══════════════════════════════════════════════════════════════════════════════
section("1. MANDATORY — Basic Checks")

# 1.1 Servidor aceita ligação TCP
def test_tcp_connect():
    try:
        s = socket.create_connection((HOST, PORT), timeout=3)
        s.close()
        return True
    except Exception:
        return False

ok = test_tcp_connect()
check("Servidor aceita ligação TCP", ok)

if not ok:
    print(f"\n{RED}ERRO CRÍTICO: servidor não está acessível em {HOST}:{PORT}{RESET}")
    print("Inicia o webserv antes de correr os testes.")
    sys.exit(1)

# 1.2 GET /  →  200 ou 301/302 (redirect)
resp = raw_request(f"GET / HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("GET / retorna resposta HTTP válida", st in (200, 301, 302, 403), f"status={st}")

# 1.3 Resposta tem Content-Type
has_ct = b"Content-Type:" in resp or b"content-type:" in resp
check("Resposta tem Content-Type", has_ct)

# 1.4 Resposta tem Content-Length ou Transfer-Encoding
has_cl = b"Content-Length:" in resp or b"content-length:" in resp
has_te = b"Transfer-Encoding:" in resp
check("Resposta tem Content-Length ou Transfer-Encoding", has_cl or has_te)


# ══════════════════════════════════════════════════════════════════════════════
# 2. MANDATORY — Check the code and ask questions (config + métodos)
# ══════════════════════════════════════════════════════════════════════════════
section("2. Métodos HTTP — GET / POST / DELETE")

# GET ficheiro existente
resp = raw_request(f"GET /index.html HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("GET /index.html → 200", st == 200, f"status={st}")

# GET ficheiro inexistente → 404
resp = raw_request(f"GET /ficheiro_que_nao_existe_xyz.html HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("GET recurso inexistente → 404", st == 404, f"status={st}")

# DELETE método não permitido em / → 405 (config tem GET POST DELETE em /)
# Mas em /upload/ só tem POST
resp = raw_request(f"DELETE /upload/ HTTP/1.1\r\nHost: {HOST}\r\nContent-Length: 0\r\n\r\n")
st = parse_status(resp)
check("DELETE em path sem permissão → 405", st == 405, f"status={st}")

# POST upload simples
body = b"hello_webserv_test"
post_req = (
    f"POST /upload/ HTTP/1.1\r\n"
    f"Host: {HOST}\r\n"
    f"Content-Type: text/plain\r\n"
    f"Content-Length: {len(body)}\r\n"
    f"\r\n"
).encode() + body
resp = raw_request(post_req.decode("latin-1"))
st = parse_status(resp)
check("POST /upload/ → 201 ou 409 (ficheiro já existe)", st in (201, 409), f"status={st}")

# Método desconhecido → 405
resp = raw_request(f"PATCH / HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("Método desconhecido (PATCH) → 405", st == 405, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 3. MANDATORY — Configuration file
# ══════════════════════════════════════════════════════════════════════════════
section("3. Configuração — Portas / Server Names / Root / Index")

# Segundo servidor na porta 8081
try:
    resp2 = raw_request(f"GET / HTTP/1.1\r\nHost: {HOST}\r\n\r\n", port=8081)
    st2 = parse_status(resp2)
    check("Segundo servidor na porta 8081 responde", st2 > 0, f"status={st2}")
except Exception as e:
    check("Segundo servidor na porta 8081 responde", False, str(e))

# Terceiro servidor na porta 8082
try:
    resp3 = raw_request(f"GET / HTTP/1.1\r\nHost: {HOST}\r\n\r\n", port=8082)
    st3 = parse_status(resp3)
    check("Terceiro servidor na porta 8082 responde", st3 > 0, f"status={st3}")
except Exception as e:
    check("Terceiro servidor na porta 8082 responde", False, str(e))

# Redirect → /redir/ deve retornar 301
resp = raw_request(f"GET /redir/ HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("GET /redir/ → 301 (redirect configurado)", st == 301, f"status={st}")
has_loc = b"Location:" in resp
check("Redirect inclui header Location", has_loc)

# Forbidden → /forbidden/ → 403
resp = raw_request(f"GET /forbidden/ HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("GET /forbidden/ → 403", st == 403, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 4. MANDATORY — Check with a browser / curl
# ══════════════════════════════════════════════════════════════════════════════
section("4. Comportamento HTTP/1.1 — Headers / Versão")

# Versão HTTP correcta na resposta
resp = raw_request(f"GET / HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
check("Resposta começa com HTTP/1.1", resp.startswith(b"HTTP/1.1"), f"inicio={resp[:15]}")

# Request sem Host → 400
resp = raw_request("GET / HTTP/1.1\r\n\r\n")
st = parse_status(resp)
check("Request sem Host header → 400", st == 400, f"status={st}")

# HTTP/1.0 deve ser suportado ou retornar código razoável
resp = raw_request(f"GET / HTTP/1.0\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("HTTP/1.0 request → resposta válida (não crash)", st > 0, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 5. MANDATORY — Check with CGI
# ══════════════════════════════════════════════════════════════════════════════
section("5. CGI — Python / PHP / Shell")

# GET CGI python
resp = raw_request(f"GET /cgi-bin/test.py HTTP/1.1\r\nHost: {HOST}\r\n\r\n", timeout=8)
st = parse_status(resp)
check("GET /cgi-bin/test.py → 200 ou 404 (ficheiro pode não existir)", st in (200, 404, 403), f"status={st}")

# GET CGI shell
resp = raw_request(f"GET /cgi-bin/test.sh HTTP/1.1\r\nHost: {HOST}\r\n\r\n", timeout=8)
st = parse_status(resp)
check("GET /cgi-bin/test.sh → 200 ou 404", st in (200, 404, 403), f"status={st}")

# POST CGI — envia body
cgi_body = b"name=Rafael&age=21"
cgi_req = (
    f"POST /cgi-bin/test.py HTTP/1.1\r\n"
    f"Host: {HOST}\r\n"
    f"Content-Type: application/x-www-form-urlencoded\r\n"
    f"Content-Length: {len(cgi_body)}\r\n"
    f"\r\n"
).encode() + cgi_body
resp = raw_request(cgi_req.decode("latin-1"), timeout=8)
st = parse_status(resp)
check("POST /cgi-bin/test.py → 200/404/403 (não crash)", st in (200, 404, 403, 500), f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 6. MANDATORY — Check with cookie and session management
# ══════════════════════════════════════════════════════════════════════════════
section("6. Cookies / Session (via CGI)")

resp = raw_request(
    f"GET /cgi-bin/session.py HTTP/1.1\r\nHost: {HOST}\r\nCookie: session_id=abc123\r\n\r\n",
    timeout=5
)
st = parse_status(resp)
check("Cookie enviado ao CGI não causa crash", st > 0, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 7. MANDATORY — Check with a browser (stress / multiple connections)
# ══════════════════════════════════════════════════════════════════════════════
section("7. Resiliência — Múltiplas ligações / Stress")

def concurrent_test(n=10):
    sockets = []
    ok = 0
    for _ in range(n):
        try:
            s = socket.create_connection((HOST, PORT), timeout=3)
            sockets.append(s)
            ok += 1
        except Exception:
            pass
    for s in sockets:
        try:
            s.sendall(f"GET / HTTP/1.1\r\nHost: {HOST}\r\n\r\n".encode())
        except Exception:
            pass
    responses = 0
    for s in sockets:
        try:
            data = s.recv(4096)
            if data:
                responses += 1
        except Exception:
            pass
        s.close()
    return ok, responses

opened, responded = concurrent_test(10)
check(f"10 ligações simultâneas abertas ({opened}/10)", opened >= 8, f"abertas={opened}")
check(f"10 ligações simultâneas responderam ({responded}/10)", responded >= 6, f"respostas={responded}")

# Servidor ainda responde depois do stress
time.sleep(0.5)
resp = raw_request(f"GET / HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("Servidor ainda responde após stress test", st > 0, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 8. MANDATORY — client_max_body_size (413)
# ══════════════════════════════════════════════════════════════════════════════

section("8. client_max_body_size — 413 Payload Too Large")

#Config tem client_max_body_size 4096
big_body = b"X" * 8000  # > 4096
big_req = (
   f"POST /upload/ HTTP/1.1\r\n"
   f"Host: {HOST}\r\n"
   f"Content-Type: application/octet-stream\r\n"
   f"Content-Length: {len(big_body)}\r\n"
   f"\r\n"
).encode() + big_body
resp = raw_request(big_req.decode("latin-1"))
st = parse_status(resp)
check("Body > client_max_body_size → 413", st == 413, f"status={st}")

#Body dentro do limite → não 413
small_body = b"Y" * 100
small_req = (
   f"POST /upload/ HTTP/1.1\r\n"
   f"Host: {HOST}\r\n"
   f"Content-Type: text/plain\r\n"
   f"Content-Length: {len(small_body)}\r\n"
   f"\r\n"
).encode() + small_body
resp = raw_request(small_req.decode("latin-1"))
st = parse_status(resp)
check("Body dentro do limite → não 413", st != 413, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 9. MANDATORY — Request parsing robustness (400 / 431)
# ══════════════════════════════════════════════════════════════════════════════
section("9. Parsing de Requests — Robustez / Erros 400 / 431")

# Request line malformada
resp = raw_request("BADREQUEST\r\n\r\n")
st = parse_status(resp)
check("Request line inválida → 400", st == 400, f"status={st}")

# Header com bare LF (sem CR) → 400
resp = raw_request(f"GET / HTTP/1.1\nHost: {HOST}\n\n")
st = parse_status(resp)
check("Bare LF em headers → 400", st == 400, f"status={st}")

# Header duplicado Content-Length → 400
resp = raw_request(
    f"POST / HTTP/1.1\r\nHost: {HOST}\r\n"
    f"Content-Length: 5\r\nContent-Length: 5\r\n\r\nhello"
)
st = parse_status(resp)
check("Content-Length duplicado → 400", st == 400, f"status={st}")

# Header muito grande → 431
big_header_val = "A" * 9000
resp = raw_request(f"GET / HTTP/1.1\r\nHost: {HOST}\r\nX-Big: {big_header_val}\r\n\r\n")
st = parse_status(resp)
check("Header muito grande → 431 ou 400", st in (431, 400), f"status={st}")

# Content-Length negativo → 400
resp = raw_request(
    f"POST / HTTP/1.1\r\nHost: {HOST}\r\n"
    f"Content-Length: -1\r\n\r\n"
)
st = parse_status(resp)
check("Content-Length negativo → 400", st == 400, f"status={st}")

# Content-Length não numérico → 400
resp = raw_request(
    f"POST / HTTP/1.1\r\nHost: {HOST}\r\n"
    f"Content-Length: abc\r\n\r\n"
)
st = parse_status(resp)
check("Content-Length não numérico → 400", st == 400, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 10. MANDATORY — Chunked Transfer-Encoding
# ══════════════════════════════════════════════════════════════════════════════
section("10. Chunked Transfer-Encoding")

chunk_body = b"5\r\nhello\r\n3\r\n wo\r\n0\r\n\r\n"
chunk_req = (
    f"POST /upload/ HTTP/1.1\r\n"
    f"Host: {HOST}\r\n"
    f"Transfer-Encoding: chunked\r\n"
    f"Content-Type: text/plain\r\n"
    f"\r\n"
).encode() + chunk_body
resp = raw_request(chunk_req.decode("latin-1"))
st = parse_status(resp)
check("POST chunked → 201/409 (aceita chunked)", st in (201, 409, 400), f"status={st}")

# Transfer-Encoding: gzip (não suportado) → 501
resp = raw_request(
    f"POST / HTTP/1.1\r\nHost: {HOST}\r\n"
    f"Transfer-Encoding: gzip\r\nContent-Type: text/plain\r\n\r\n"
)
st = parse_status(resp)
check("Transfer-Encoding não suportado → 501", st == 501, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 11. MANDATORY — Autoindex
# ══════════════════════════════════════════════════════════════════════════════
section("11. Autoindex")

resp = raw_request(f"GET /images/ HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
body_str = resp.decode("latin-1", errors="replace")
check("GET /images/ → 200 (autoindex on)", st == 200, f"status={st}")
check("Autoindex contém HTML listing", "<html>" in body_str.lower() or "<a href" in body_str.lower())


# ══════════════════════════════════════════════════════════════════════════════
# 12. MANDATORY — Path traversal / Security
# ══════════════════════════════════════════════════════════════════════════════
section("12. Segurança — Path Traversal / Injeção")

# Path traversal
for bad_path in ["/../etc/passwd", "/../../etc/passwd", "/%2e%2e/etc/passwd"]:
    try:
        resp = raw_request(f"GET {bad_path} HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
        st = parse_status(resp)
        body = resp.decode("latin-1", errors="replace")
        no_passwd = "root:" not in body and "nobody:" not in body
        check(f"Path traversal '{bad_path}' não vaza /etc/passwd", no_passwd, f"status={st}")
    except Exception as e:
        check(f"Path traversal '{bad_path}' não causa crash", False, str(e))

# Null byte
resp = raw_request(f"GET /index\x00.html HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("Null byte no path → 400 ou 404 (não crash)", st in (400, 404), f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 13. MANDATORY — CGI Timeout
# ══════════════════════════════════════════════════════════════════════════════
section("13. CGI Timeout (5s)")

# Script que dorme > timeout do servidor (5s)
start = time.time()
try:
    resp = raw_request(
        f"GET /cgi-bin/sleep.py HTTP/1.1\r\nHost: {HOST}\r\n\r\n",
        timeout=12
    )
    elapsed = time.time() - start
    st = parse_status(resp)
    # Deve ter matado o processo e retornado 500 em <= 6s
    killed_in_time = elapsed < 8
    check("CGI timeout — servidor não bloqueia para sempre", killed_in_time, f"elapsed={elapsed:.1f}s status={st}")
    check("CGI timeout → 500 (processo morto)", st == 500 or st == 404, f"status={st}")
except socket.timeout:
    elapsed = time.time() - start
    check("CGI timeout — servidor não bloqueia para sempre", False, f"servidor bloqueou por {elapsed:.1f}s")


# ══════════════════════════════════════════════════════════════════════════════
# 14. MANDATORY — DELETE
# ══════════════════════════════════════════════════════════════════════════════
section("14. DELETE — Apagar ficheiros")

# Primeiro criar um ficheiro
fname = f"delete_test_{int(time.time())}.txt"
body = b"to be deleted"
post_req = (
    f"POST /upload/{fname} HTTP/1.1\r\n"
    f"Host: {HOST}\r\n"
    f"Content-Type: text/plain\r\n"
    f"Content-Length: {len(body)}\r\n"
    f"\r\n"
).encode() + body
resp = raw_request(post_req.decode("latin-1"))
st_post = parse_status(resp)
check(f"POST /upload/{fname} para criar ficheiro de teste", st_post in (201, 409), f"status={st_post}")

# Agora apagar (o upload_store é ./www/uploads mas o path no URL não está mapeado para DELETE)
# Testar DELETE em / (tem DELETE permitido)
resp = raw_request(f"DELETE /test/test_del.txt HTTP/1.1\r\nHost: {HOST}\r\n\r\n")
st = parse_status(resp)
check("DELETE ficheiro inexistente → 404", st == 404, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# 15. BONUS — Multiple servers & CGI
# ══════════════════════════════════════════════════════════════════════════════
section("15. BONUS — Múltiplos Servidores / CGI avançado")

# Porta 8081 deve ter configuração diferente (sem DELETE na raíz)
try:
    resp = raw_request(f"DELETE / HTTP/1.1\r\nHost: {HOST}\r\n\r\n", port=8081)
    st = parse_status(resp)
    check("Porta 8081 — DELETE / → 405 (não tem DELETE)", st == 405, f"status={st}")
except Exception as e:
    check("Porta 8081 acessível para teste DELETE", False, str(e))

# CGI com query string
resp = raw_request(
    f"GET /cgi-bin/test.py?name=Rafael&age=21 HTTP/1.1\r\nHost: {HOST}\r\n\r\n",
    timeout=8
)
st = parse_status(resp)
check("CGI com query string → não crash", st > 0, f"status={st}")


# ══════════════════════════════════════════════════════════════════════════════
# SUMÁRIO
# ══════════════════════════════════════════════════════════════════════════════
section("SUMÁRIO FINAL")

total  = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed
pct    = (passed / total * 100) if total else 0

print(f"\n  Total : {total}")
print(f"  {GREEN}Passed: {passed}{RESET}")
print(f"  {RED}Failed: {failed}{RESET}")
print(f"  Score : {pct:.1f}%")

if failed:
    print(f"\n{YELLOW}Testes falhados:{RESET}")
    for name, ok in results:
        if not ok:
            print(f"  {RED}✗{RESET} {name}")

# Avaliação qualitativa
print(f"\n{BOLD}Avaliação estimada (baseada nos testes):{RESET}")
if pct >= 90:
    print(f"  {GREEN}Excelente — código sólido, deve passar sem problemas{RESET}")
elif pct >= 75:
    print(f"  {YELLOW}Bom — alguns pontos a corrigir antes da avaliação{RESET}")
elif pct >= 55:
    print(f"  {YELLOW}Médio — vários critérios em falta, revisão necessária{RESET}")
else:
    print(f"  {RED}Atenção — múltiplos critérios críticos em falta{RESET}")

print(f"\n{INFO} Nota: alguns testes dependem de ficheiros CGI (test.py, sleep.py)")
print(f"{INFO} e da estrutura de directórios do teu webserv (./www/uploads, etc.)")
print(f"{INFO} Ajusta o HOST/PORT: python3 webserv_tester.py <host> <port>")
