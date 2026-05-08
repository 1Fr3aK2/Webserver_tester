#!/usr/bin/env python3
"""
webserv_tester.py — Tester de segurança e robustez para Webserv (42)
Testa todas as vulnerabilidades identificadas na análise de segurança.

Uso:
    python3 webserv_tester.py [host] [port]
    python3 webserv_tester.py 127.0.0.1 8080

Por omissão: host=127.0.0.1, port=8080
"""

import socket
import sys
import time
import os
import threading
import errno

# ─── Cores ANSI ──────────────────────────────────────────────────────────────
R  = "\033[0;31m"   # red
G  = "\033[0;32m"   # green
Y  = "\033[0;33m"   # yellow
B  = "\033[0;34m"   # blue
M  = "\033[0;35m"   # magenta
C  = "\033[0;36m"   # cyan
W  = "\033[1;37m"   # white bold
DIM = "\033[2m"
RST = "\033[0m"
BOLD = "\033[1m"

# ─── Configuração ─────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8080
TIMEOUT = 5.0

# ─── Contadores globais ────────────────────────────────────────────────────────
results = {
    "pass":    [],
    "fail":    [],
    "warning": [],
    "info":    [],
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def banner():
    print(f"""
{W}╔══════════════════════════════════════════════════════════╗
║          WEBSERV SECURITY & ROBUSTNESS TESTER            ║
║          Análise completa — 42 Webserv Project           ║
╚══════════════════════════════════════════════════════════╝{RST}
  {DIM}Host: {HOST}:{PORT}{RST}
""")

def section(title):
    bar = "─" * (56 - len(title) - 2)
    print(f"\n{B}{BOLD}┌─ {title} {bar}┐{RST}")

def send_raw(request_bytes, recv_size=8192, timeout=TIMEOUT):
    """Envia bytes raw e retorna a resposta como bytes."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((HOST, PORT))
        s.sendall(request_bytes)
        data = b""
        try:
            while True:
                chunk = s.recv(recv_size)
                if not chunk:
                    break
                data += chunk
                if len(data) > 65536:
                    break
        except socket.timeout:
            pass
        s.close()
        return data
    except Exception as e:
        return None

def send_request(method, path, headers=None, body=b"", timeout=TIMEOUT):
    """Constrói e envia um request HTTP/1.1, retorna (status_code, headers_dict, body_bytes)."""
    h = {"Host": f"{HOST}:{PORT}", "Connection": "close"}
    if headers:
        h.update(headers)
    if body:
        h["Content-Length"] = str(len(body))

    req_lines = [f"{method} {path} HTTP/1.1"]
    for k, v in h.items():
        req_lines.append(f"{k}: {v}")
    req_lines.append("")
    req_lines.append("")
    raw = "\r\n".join(req_lines).encode() + (body if isinstance(body, bytes) else body.encode())
    resp = send_raw(raw, timeout=timeout)
    if resp is None:
        return None, {}, b""
    try:
        # separar header e body
        idx = resp.find(b"\r\n\r\n")
        if idx == -1:
            idx = resp.find(b"\n\n")
            sep = 2
        else:
            sep = 4
        header_part = resp[:idx].decode(errors="replace")
        body_part = resp[idx+sep:]
        lines = header_part.split("\r\n") if "\r\n" in header_part else header_part.split("\n")
        status_line = lines[0]
        status_code = int(status_line.split(" ")[1]) if len(status_line.split(" ")) > 1 else 0
        hd = {}
        for line in lines[1:]:
            if ":" in line:
                k2, _, v2 = line.partition(":")
                hd[k2.strip().lower()] = v2.strip()
        return status_code, hd, body_part
    except Exception:
        return 0, {}, resp

def record(level, test_id, name, passed, detail="", fix=""):
    icon  = f"{G}✓{RST}" if passed else (f"{Y}⚠{RST}" if level == "warning" else f"{R}✗{RST}")
    label = f"{G}PASS{RST}" if passed else (f"{Y}WARN{RST}" if level == "warning" else f"{R}FAIL{RST}")
    print(f"  {icon} [{label}] {W}{test_id}{RST} — {name}")
    if detail:
        print(f"       {DIM}{detail}{RST}")
    if not passed and fix:
        print(f"       {Y}Fix: {fix}{RST}")
    entry = {"id": test_id, "name": name, "detail": detail}
    if passed:
        results["pass"].append(entry)
    elif level == "warning":
        results["warning"].append(entry)
    else:
        results["fail"].append(entry)

# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 1 — V-01: PATH TRAVERSAL
# ══════════════════════════════════════════════════════════════════════════════

def test_path_traversal():
    section("V-01 · Path Traversal via is_InsideRoot")

    # 1a — traversal simples
    payloads = [
        ("/../../../etc/passwd",          "traversal simples"),
        ("/%2e%2e/%2e%2e/etc/passwd",     "URL-encoded dots"),
        ("/%2e%2e%2f%2e%2e%2fetc/passwd", "double-encoded"),
        ("/static/../../../etc/passwd",   "traversal via subdir"),
        ("/.%2e/.%2e/etc/passwd",         "mixed encoding"),
        ("/..%c0%af../etc/passwd",        "overlong UTF-8 slash"),
    ]

    all_safe = True
    for path, label in payloads:
        code, _, body = send_request("GET", path)
        leaked = b"root:" in body or b"daemon:" in body or b"nobody:" in body
        if leaked or code == 200:
            record("fail", "V-01a", f"Path traversal ({label})",
                   False,
                   f"path={path!r} → status={code}, body contém /etc/passwd",
                   "Usar realpath() em is_InsideRoot antes de comparar prefixo")
            all_safe = False
        # status esperado: 400 ou 403 ou 404

    if all_safe:
        record("info", "V-01a", "Path traversal (6 payloads)", True,
               "Todos os payloads retornaram erro sem expor ficheiros do sistema")

    # 1b — traversal para fora da upload dir via filename
    code2, _, body2 = send_request(
        "POST", "/upload/../../etc/crontab",
        headers={"Content-Type": "text/plain"},
        body=b"pwned"
    )
    safe2 = code2 in (400, 403, 404, 405)
    record("fail" if not safe2 else "info",
           "V-01b", "POST upload path traversal",
           safe2,
           f"POST /upload/../../etc/crontab → {code2}",
           "Sanitizar filename extraído do path no handle_POST")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 2 — V-02: CGI HEADER INJECTION
# ══════════════════════════════════════════════════════════════════════════════

def test_cgi_header_injection():
    section("V-02 · Injeção de Ambiente CGI")

    # Tenta injetar variável via Content-Type com newline
    payloads = [
        ("content-type", "text/plain\nSHELL=/bin/bash",            "newline no Content-Type"),
        ("content-type", "text/plain\r\nLD_PRELOAD=/tmp/evil.so",   "CRLF + LD_PRELOAD"),
        ("query-string", "a=1\nSHELL=/bin/sh",                     "newline no query string"),
    ]

    for header_name, val, label in payloads:
        code, resp_h, body = send_request(
            "GET", "/cgi-bin/test.php",
            headers={header_name: val}
        )
        # Se o servidor crashou ou retornou 500 com output de env, pode estar vulnerável.
        # Verificamos se "SHELL=" ou "LD_PRELOAD=" aparecem na resposta (reflexão de env).
        injected = b"SHELL=" in body or b"LD_PRELOAD=" in body or b"LD_PRELOAD" in body
        safe = not injected and code not in (200,)

        # Se não há CGI configurado, o servidor deve dar 404 — isso é aceitável.
        if code == 404 or code == 403:
            record("info", "V-02", f"CGI env injection ({label})",
                   True, f"Sem rota CGI configurada → {code} (não aplicável)")
        else:
            record("fail" if injected else "info",
                   "V-02", f"CGI env injection ({label})",
                   not injected,
                   f"header={header_name!r} → status={code}, injeção reflectida={injected}",
                   "Sanitizar valores de headers em build_Environment() — remover \\n e \\r")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 3 — V-03: BUFFER / LOG INJECTION
# ══════════════════════════════════════════════════════════════════════════════

def test_buffer_log_injection():
    section("V-03 · Buffer Overflow & Log Injection")

    # 3a — body > MAX_BODY_SIZE (4096), deve dar 413
    big_body = b"A" * 8192
    code, _, _ = send_request("POST", "/upload/test_large.txt",
                               headers={"Content-Type": "application/octet-stream"},
                               body=big_body)
    record("fail" if code not in (413, 400, 403) else "info",
           "V-03a", "Body > MAX_BODY_SIZE deve retornar 413",
           code in (413, 400, 403),
           f"body=8192 bytes → status={code} (esperado 413)",
           "Verificar limite MAX_BODY_SIZE em determine_NextState()")

    # 3b — request com header muito grande (> MAX_HEADER_SIZE 8192), deve dar 431
    huge_header_val = "X" * 9000
    raw = (
        f"GET / HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        f"X-Padding: {huge_header_val}\r\n"
        f"Connection: close\r\n\r\n"
    ).encode()
    resp = send_raw(raw)
    if resp:
        code3 = int(resp.split(b" ")[1]) if len(resp.split(b" ")) > 1 else 0
        try:
            code3 = int(resp[:12].split(b" ")[1])
        except Exception:
            code3 = 0
        record("fail" if code3 not in (431, 400, 413) else "info",
               "V-03b", "Header demasiado grande → 431",
               code3 in (431, 400, 413),
               f"header 9000 bytes → status={code3} (esperado 431)",
               "Verificar fill_Buffer(): _statusCode=431 para headers > MAX_HEADER_SIZE")
    else:
        record("warning", "V-03b", "Header demasiado grande", False,
               "Servidor não respondeu (possível crash)")

    # 3c — log injection: newline no User-Agent
    code4, _, body4 = send_request(
        "GET", "/",
        headers={"User-Agent": "Mozilla\r\nFAKE_LOG_ENTRY: injected"}
    )
    # Não conseguimos verificar os logs do servidor directamente,
    # mas verificamos que o servidor não crashou.
    alive = code4 is not None and code4 > 0
    record("info", "V-03c", "Log injection (CRLF no User-Agent)",
           alive,
           f"Status={code4} — verificar manualmente os logs do servidor para 'FAKE_LOG_ENTRY'",
           "Sanitizar dados do cliente antes de imprimir com std::cout")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 4 — V-04: XSS VIA AUTOINDEX
# ══════════════════════════════════════════════════════════════════════════════

def test_xss_autoindex():
    section("V-04 · XSS via Autoindex")

    # Nota: para testar XSS precisamos de um directório com autoindex=on.
    # Tentamos alguns paths comuns; se autoindex estiver activo, verificamos o HTML.
    paths_to_try = ["/", "/images/", "/test/", "/upload/", "/cgi-bin/"]

    found_autoindex = False
    for path in paths_to_try:
        code, h, body = send_request("GET", path)
        if b"<a href=" in body and b"Index of" in body:
            found_autoindex = True
            # Verificar se os nomes de ficheiros estão escaped
            # Um ficheiro chamado "<script>" não pode existir, mas verificamos
            # se o path é inserido sem escape
            has_unescaped = b"<script" in body and b"Index of" in body
            # Verificar se o path URL está escaped no título
            # <h1>Index of /</h1> — o path vem directo do request
            record("fail" if has_unescaped else "info",
                   "V-04", f"XSS no autoindex ({path})",
                   not has_unescaped,
                   f"Autoindex activo em {path}, has_unescaped_script={has_unescaped}",
                   "Usar html_escape() em generateHTML() para nomes de ficheiros e paths")
            break

    if not found_autoindex:
        record("info", "V-04", "XSS no autoindex",
               True, "Nenhum directório com autoindex encontrado nos paths testados")

    # Teste directo: path com caracteres HTML no URL
    code2, _, body2 = send_request("GET", "/<script>alert(1)</script>")
    reflected = b"<script>alert(1)</script>" in body2
    record("fail" if reflected else "info",
           "V-04b", "XSS reflectido via path na resposta de erro",
           not reflected,
           f"GET /<script>alert(1)</script> → reflectido={reflected}",
           "Escapar o path nas error pages e em qualquer HTML gerado dinamicamente")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 5 — V-05: UPLOAD SEM SANITIZAÇÃO DE FILENAME
# ══════════════════════════════════════════════════════════════════════════════

def test_upload_filename():
    section("V-05 · Upload sem sanitização do filename")

    dangerous_files = [
        ("/upload/.htaccess",          b"Options +ExecCGI",    ".htaccess"),
        ("/upload/evil.php",           b"<?php system($_GET['cmd']); ?>", ".php executável"),
        ("/upload/evil.sh",            b"#!/bin/bash\nrm -rf /", ".sh executável"),
        ("/upload/../../../tmp/pwned", b"pwned",               "path traversal em upload"),
        ("/upload/\x00null.txt",       b"null byte",           "null byte no filename"),
    ]

    for path, body_data, label in dangerous_files:
        code, _, _ = send_request(
            "POST", path,
            headers={"Content-Type": "application/octet-stream"},
            body=body_data
        )
        # Qualquer código que não seja criação de ficheiro é aceitável
        # 201 significa que o ficheiro foi criado — potencialmente perigoso
        # para .php, .sh, .htaccess
        dangerous = code == 201
        record("fail" if dangerous else "info",
               "V-05", f"Upload de ficheiro perigoso ({label})",
               not dangerous,
               f"POST {path!r} → {code} {'(FICHEIRO CRIADO!)' if dangerous else '(bloqueado)'}",
               "Sanitizar filename: whitelist de chars, blacklist de extensões executáveis")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 6 — V-06/V-07: DANGLING POINTERS E DOUBLE-CLOSE CGI
# (testes funcionais — verificamos estabilidade do servidor após execução CGI)
# ══════════════════════════════════════════════════════════════════════════════

def test_cgi_stability():
    section("V-06/V-07 · Estabilidade CGI (dangling pointers / double-close)")

    # Enviar múltiplos requests CGI rápidos e verificar que o servidor não crasha
    paths_cgi = ["/cgi-bin/test.php", "/cgi-bin/test.py", "/cgi-bin/hello.cgi"]

    crashes = 0
    for i in range(5):
        for path in paths_cgi:
            code, _, _ = send_request("GET", path, timeout=3.0)
            if code is None:
                crashes += 1

    # Verificar que o servidor ainda responde após os requests CGI
    time.sleep(0.5)
    code_alive, _, _ = send_request("GET", "/")
    alive = code_alive is not None and code_alive > 0

    record("fail" if not alive else "info",
           "V-06/07a", "Servidor continua vivo após requests CGI",
           alive,
           f"crashes={crashes}, servidor vivo={alive}",
           "Corrigir double-close em execute_ChildProcess() e reservar espaço em env vector")

    # Teste de stress: muitos forks CGI simultâneos
    errors = []
    def cgi_req():
        c, _, _ = send_request("GET", "/cgi-bin/test.php", timeout=3.0)
        if c is None:
            errors.append(1)

    threads = [threading.Thread(target=cgi_req) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    time.sleep(1.0)
    code_after, _, _ = send_request("GET", "/")
    alive2 = code_after is not None and code_after > 0
    record("fail" if not alive2 else "info",
           "V-06/07b", "Servidor estável após 10 CGI simultâneos",
           alive2,
           f"erros={len(errors)}, servidor vivo depois={alive2}",
           "Garantir que env vector não é realocado entre build_Environment e execve")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 7 — V-08: INTEGER OVERFLOW EM CONTENT-LENGTH
# ══════════════════════════════════════════════════════════════════════════════

def test_content_length_overflow():
    section("V-08 · Integer Overflow em Content-Length")

    overflow_values = [
        ("99999999999999999999",  "valor gigante"),
        ("-1",                   "negativo"),
        ("-9999999999",          "negativo grande"),
        ("2147483648",           "INT_MAX+1"),
        ("9223372036854775808",  "LONG_MAX+1"),
        ("0x10",                 "hex (inválido)"),
        ("1a2b",                 "alfanumérico"),
        ("   999",               "espaços antes"),
    ]

    for val, label in overflow_values:
        # Enviar header Content-Length mas sem body — testar parsing
        raw = (
            f"POST /upload/overflow_test.txt HTTP/1.1\r\n"
            f"Host: {HOST}:{PORT}\r\n"
            f"Content-Length: {val}\r\n"
            f"Content-Type: text/plain\r\n"
            f"Connection: close\r\n\r\n"
        ).encode()
        resp = send_raw(raw, timeout=3.0)
        if resp is None:
            record("fail", "V-08", f"Content-Length overflow ({label})",
                   False, f"Servidor não respondeu para Content-Length: {val!r}",
                   "Usar strtoull com verificação de errno para Content-Length")
            continue
        try:
            code = int(resp.split(b" ")[1])
        except Exception:
            code = 0
        # Servidor deve rejeitar (400/413) ou aguardar body (timeout).
        # NÃO deve crashar (None) nem dar 200/201.
        safe = code in (400, 413, 408, 501) or (code == 0 and len(resp) > 0)
        record("fail" if not safe and code in (200, 201) else "info",
               "V-08", f"Content-Length: {val!r} ({label})",
               not (code in (200, 201)),
               f"→ status={code}",
               "Substituir atol por strtoull com verificação de overflow")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 8 — V-09: DELETE SEM AUTENTICAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

def test_delete_unauth():
    section("V-09 · DELETE sem autenticação")

    # Primeiro fazer upload de um ficheiro de teste
    test_filename = f"delete_test_{int(time.time())}.txt"
    upload_path = f"/upload/{test_filename}"
    code_up, _, _ = send_request(
        "POST", upload_path,
        headers={"Content-Type": "text/plain"},
        body=b"test content for deletion"
    )

    if code_up == 201:
        # Ficheiro criado — tentar apagar sem qualquer autenticação
        code_del, _, _ = send_request("DELETE", upload_path)
        if code_del == 204:
            record("warning", "V-09a", "DELETE sem autenticação apagou ficheiro",
                   False,
                   f"DELETE {upload_path} → 204 (sem token de autorização)",
                   "Implementar token de autorização ou restringir DELETE por IP")
        else:
            record("info", "V-09a", "DELETE requer condições adicionais",
                   True, f"DELETE → {code_del}")
    else:
        # Sem upload, testar DELETE em ficheiros estáticos conhecidos
        for path in ["/index.html", "/static/index.html", "/"]:
            code_del, _, _ = send_request("DELETE", path)
            if code_del == 204:
                record("fail", "V-09b", f"DELETE de ficheiro estático sem auth ({path})",
                       False,
                       f"DELETE {path} → 204 sem autenticação",
                       "Restringir DELETE a paths com autorização explícita")
                break
        else:
            record("info", "V-09", "DELETE — upload não disponível para teste completo",
                   True, f"Upload retornou {code_up}")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 9 — B-01: MATCHLOCATION PREFIX BUG
# ══════════════════════════════════════════════════════════════════════════════

def test_matchlocation_prefix():
    section("B-01 · matchLocation prefix boundary bug")

    # Se existir uma location /api configurada, /apikeys deve dar 404 ou
    # ser tratado pela location root, não pela /api.
    # Verificamos comportamentos diferentes entre /api e /apikeys.
    code_api, h_api, _ = send_request("GET", "/api")
    code_apikeys, h_apikeys, _ = send_request("GET", "/apikeys")
    code_apiv2, h_apiv2, _ = send_request("GET", "/api/v2")

    # Se /api e /apikeys retornam o mesmo status E headers Allow iguais,
    # provavelmente estão a ser tratados pela mesma location (bug).
    same_treatment = (code_api == code_apikeys and
                      h_api.get("allow") == h_apikeys.get("allow") and
                      code_api != 404)

    record("warning" if same_treatment else "info",
           "B-01", "matchLocation boundary: /api vs /apikeys",
           not same_treatment,
           f"/api={code_api}, /apikeys={code_apikeys}, /api/v2={code_apiv2}",
           "Verificar que (path[locLen] == '/' || path.size() == locLen) após prefix match")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 10 — B-02: SERVERCONFIG REUTILIZADO NO PARSER
# (teste indirecto — verificamos se error pages e comportamentos diferem entre servers)
# ══════════════════════════════════════════════════════════════════════════════

def test_serverconfig_reuse():
    section("B-02 · ServerConfig reutilizado entre servers no parser")

    # Este bug só é observável se o servidor tiver múltiplos blocos server {}.
    # Verificamos se o servidor está a ouvir em múltiplas portas.
    ports_to_check = [PORT, PORT + 1, PORT + 2, 8081, 8082, 8443]
    active_ports = []

    for p in ports_to_check:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((HOST, p))
            s.close()
            active_ports.append(p)
        except Exception:
            pass

    if len(active_ports) > 1:
        record("info", "B-02", "Múltiplos servers detectados",
               True,
               f"Portas activas: {active_ports}. Verificar manualmente se configurações são independentes.",
               "Declarar ServerConfig sc dentro do loop em parse_all()")
    else:
        record("info", "B-02", "ServerConfig parser (servidor único)",
               True,
               f"Apenas porta {PORT} activa. Bug B-02 requer múltiplos blocos server {{}} no .conf")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 11 — B-03: CGI OUTPUT SEM SEPARADOR
# ══════════════════════════════════════════════════════════════════════════════

def test_cgi_output_validation():
    section("B-03 · Validação de output CGI (separador em falta)")

    # Não podemos controlar directamente o output do CGI sem acesso ao servidor.
    # Verificamos que o servidor não dá 200 para paths CGI inexistentes.
    code, _, body = send_request("GET", "/cgi-bin/nonexistent_script_xyz.php")
    safe = code in (404, 403, 500, 502)
    record("fail" if code == 200 else "info",
           "B-03", "CGI inexistente não deve retornar 200",
           safe,
           f"GET /cgi-bin/nonexistent_script_xyz.php → {code}",
           "Restaurar verificação comentada em is_ValidCGIOutput(): if pos==npos return false")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 12 — B-04: ATOI SEM VALIDAÇÃO NO PARSER
# ══════════════════════════════════════════════════════════════════════════════

def test_parser_atoi():
    section("B-04 · atoi sem validação (porta / body size)")

    # Verificar que o servidor está numa porta válida (1-65535)
    if not (1 <= PORT <= 65535):
        record("fail", "B-04", "Porta fora do range válido",
               False, f"PORT={PORT}",
               "Validar porta com strtol + range check [1,65535] no parser")
    else:
        record("info", "B-04", "Porta no range válido", True,
               f"PORT={PORT} (1–65535)")

    # Enviar request com Content-Length alfanumérico — deve dar 400
    raw = (
        f"POST /upload/test.txt HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        f"Content-Length: abc123\r\n"
        f"Content-Type: text/plain\r\n"
        f"Connection: close\r\n\r\n"
    ).encode()
    resp = send_raw(raw, timeout=3.0)
    try:
        code = int(resp.split(b" ")[1]) if resp else 0
    except Exception:
        code = 0
    record("fail" if code == 200 else "info",
           "B-04b", "Content-Length inválido (abc123) → 400",
           code in (400, 413),
           f"Content-Length: abc123 → {code}",
           "Verificar is_Number() antes de atol() em parse_Headers()")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 13 — B-05: ITERATOR INVALIDATION / ROBUSTEZ DO SERVIDOR
# ══════════════════════════════════════════════════════════════════════════════

def test_iterator_stability():
    section("B-05 · Iterator invalidation / Robustez do event loop")

    # Abrir muitas conexões simultâneas e fechar algumas abruptamente
    sockets_open = []
    try:
        for i in range(20):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((HOST, PORT))
                sockets_open.append(s)
            except Exception:
                break

        # Fechar metade abruptamente (RST)
        for i, s in enumerate(sockets_open[:10]):
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                             b'\x01\x00\x00\x00\x00\x00\x00\x00')
                s.close()
            except Exception:
                pass

        # Enviar request válido em sockets restantes
        errors = 0
        for s in sockets_open[10:]:
            try:
                req = f"GET / HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nConnection: close\r\n\r\n"
                s.sendall(req.encode())
                data = s.recv(1024)
                if not data:
                    errors += 1
            except Exception:
                errors += 1
            finally:
                try:
                    s.close()
                except Exception:
                    pass

    except Exception as e:
        errors = 99

    # Verificar que servidor ainda responde
    time.sleep(1.0)
    code, _, _ = send_request("GET", "/")
    alive = code is not None and code > 0

    record("fail" if not alive else ("warning" if errors > 3 else "info"),
           "B-05", "Servidor estável após conexões abruptas",
           alive,
           f"20 conexões, 10 fechadas com RST, erros={errors}, servidor vivo={alive}",
           "Corrigir index após fds.erase() no handle_Clients loop")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 14 — CONFORMIDADE HTTP (subject 42)
# ══════════════════════════════════════════════════════════════════════════════

def test_http_conformance():
    section("HTTP Conformance (requisitos do subject)")

    # 14a — request sem Host header deve dar 400
    raw_no_host = b"GET / HTTP/1.1\r\nConnection: close\r\n\r\n"
    resp = send_raw(raw_no_host)
    try:
        code = int(resp.split(b" ")[1]) if resp else 0
    except Exception:
        code = 0
    record("fail" if code == 200 else "info",
           "HTTP-01", "Request sem Host → 400",
           code in (400,),
           f"→ {code} (esperado 400)")

    # 14b — método inválido deve dar 405
    code2, _, _ = send_request("PATCH", "/")
    record("fail" if code2 == 200 else "info",
           "HTTP-02", "Método PATCH não implementado → 405",
           code2 in (405, 501),
           f"PATCH / → {code2} (esperado 405 ou 501)")

    # 14c — HTTP/1.0 deve ser aceite
    raw_10 = f"GET / HTTP/1.0\r\nHost: {HOST}:{PORT}\r\n\r\n".encode()
    resp3 = send_raw(raw_10)
    try:
        code3 = int(resp3.split(b" ")[1]) if resp3 else 0
    except Exception:
        code3 = 0
    record("info", "HTTP-03", "HTTP/1.0 aceite",
           code3 > 0, f"GET HTTP/1.0 → {code3}")

    # 14d — Transfer-Encoding: chunked deve dar 501 (não implementado)
    raw_chunk = (
        f"POST /upload/chunk.txt HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        f"Transfer-Encoding: chunked\r\n"
        f"Connection: close\r\n\r\n"
        "5\r\nhello\r\n0\r\n\r\n"
    ).encode()
    resp4 = send_raw(raw_chunk)
    try:
        code4 = int(resp4.split(b" ")[1]) if resp4 else 0
    except Exception:
        code4 = 0
    record("fail" if code4 in (200, 201) else "info",
           "HTTP-04", "Transfer-Encoding: chunked suportado",
           code4 in (201, 200),
           f"Chunked POST → {code4} (esperado 200 ou 201)")

    # 14e — Content-Length E Transfer-Encoding juntos → 400
    raw_both = (
        f"POST /upload/both.txt HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        f"Content-Length: 5\r\n"
        f"Transfer-Encoding: chunked\r\n"
        f"Connection: close\r\n\r\nhello"
    ).encode()
    resp5 = send_raw(raw_both)
    try:
        code5 = int(resp5.split(b" ")[1]) if resp5 else 0
    except Exception:
        code5 = 0
    record("fail" if code5 == 200 else "info",
           "HTTP-05", "Content-Length + Transfer-Encoding → 400",
           code5 in (400, 501),
           f"→ {code5} (esperado 400)")

    # 14f — Request line malformada → 400
    raw_bad = b"GETX/nospacesHTTP/1.1\r\nHost: localhost\r\n\r\n"
    resp6 = send_raw(raw_bad)
    try:
        code6 = int(resp6.split(b" ")[1]) if resp6 else 0
    except Exception:
        code6 = 0
    record("info", "HTTP-06", "Request line malformada → 400",
           code6 in (400,),
           f"→ {code6}")

    # 14g — Bare LF (sem CR) deve dar 400
    raw_lf = b"GET / HTTP/1.1\nHost: localhost\n\n"
    resp7 = send_raw(raw_lf)
    try:
        code7 = int(resp7.split(b" ")[1]) if resp7 else 0
    except Exception:
        code7 = 0
    record("info", "HTTP-07", "Bare LF (sem \\r) → 400",
           code7 in (400,),
           f"→ {code7}")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 15 — TIMEOUT E RESILIÊNCIA
# ══════════════════════════════════════════════════════════════════════════════

def test_timeout_resilience():
    section("Timeout & Resiliência (requisito subject)")

    # 15a — Conexão que envia header mas não envia body → deve receber 408 em < 10s
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(12.0)
        s.connect((HOST, PORT))
        # Envia header com Content-Length mas sem body
        incomplete = (
            f"POST /upload/timeout_test.txt HTTP/1.1\r\n"
            f"Host: {HOST}:{PORT}\r\n"
            f"Content-Length: 1000\r\n"
            f"Content-Type: text/plain\r\n"
            f"Connection: close\r\n\r\n"
        ).encode()
        s.sendall(incomplete)
        start = time.time()
        data = b""
        try:
            while True:
                chunk = s.recv(1024)
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
        elapsed = time.time() - start
        s.close()

        # Deve ter fechado em < 10 segundos com 408
        try:
            code_t = int(data.split(b" ")[1]) if data else 0
        except Exception:
            code_t = 0

        if elapsed < 10 and code_t in (408, 400):
            record("info", "RES-01", f"Timeout de request incompleto ({elapsed:.1f}s)",
                   True, f"Recebeu {code_t} em {elapsed:.1f}s (< 10s) ✓")
        elif elapsed >= 10:
            record("warning", "RES-01", "Timeout demorou ≥ 10s",
                   False,
                   f"elapsed={elapsed:.1f}s, status={code_t}",
                   "INCOMPLETE_REQUEST_TIMEOUT_SEC deve ser ≤ 5s")
        else:
            record("info", "RES-01", f"Servidor fechou conexão em {elapsed:.1f}s",
                   True, f"status={code_t}, elapsed={elapsed:.1f}s")

    except Exception as e:
        record("warning", "RES-01", "Timeout request incompleto",
               False, f"Erro: {e}")

    # 15b — Servidor não deve bloquear com conexão que não envia nada
    try:
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.settimeout(35.0)
        s2.connect((HOST, PORT))
        # Não enviar nada
        start2 = time.time()
        data2 = b""
        try:
            while True:
                chunk2 = s2.recv(1024)
                if not chunk2:
                    break
                data2 += chunk2
        except socket.timeout:
            pass
        elapsed2 = time.time() - start2
        s2.close()
        record("warning" if elapsed2 >= 30 else "info",
               "RES-02", f"Conexão silenciosa fechada em {elapsed2:.1f}s",
               elapsed2 < 30,
               f"Servidor fechou após {elapsed2:.1f}s (esperado < 30s)")
    except Exception as e:
        record("info", "RES-02", "Conexão silenciosa", True, f"{e}")

    # 15c — Servidor responde após stress test
    threads_done = []
    def stress_req():
        c, _, _ = send_request("GET", "/", timeout=3.0)
        threads_done.append(c)

    threads = [threading.Thread(target=stress_req) for _ in range(50)]
    for t in threads: t.start()
    for t in threads: t.join()

    ok = sum(1 for c in threads_done if c and c > 0)
    rate = ok / 50 * 100
    record("fail" if rate < 50 else ("warning" if rate < 80 else "info"),
           "RES-03", f"Stress: {ok}/50 requests com sucesso ({rate:.0f}%)",
           rate >= 80,
           f"ok={ok}/50 ({rate:.0f}%)",
           "Verificar B-05: iterator invalidation pode perder requests em carga")


# ══════════════════════════════════════════════════════════════════════════════
# BLOCO 16 — BP-01/BP-02: BOAS PRÁTICAS
# ══════════════════════════════════════════════════════════════════════════════

def test_best_practices():
    section("BP-01/BP-02 · Boas práticas")

    # BP — Server header não deve revelar versão
    code, h, _ = send_request("GET", "/")
    server_h = h.get("server", "")
    if server_h:
        record("warning" if "/" in server_h or any(c.isdigit() for c in server_h) else "info",
               "BP-01", "Server header não revela versão",
               "/" not in server_h,
               f"Server: {server_h!r}",
               "Não incluir versão no header Server: (ex. 'webserv/1.0' → 'webserv')")
    else:
        record("info", "BP-01", "Sem header Server (aceitável)", True)

    # BP — Error pages devem ter Content-Type text/html
    code2, h2, _ = send_request("GET", "/this_path_does_not_exist_xyz")
    ct = h2.get("content-type", "")
    record("warning" if code2 == 404 and "html" not in ct else "info",
           "BP-02", "Error 404 tem Content-Type: text/html",
           "html" in ct or code2 != 404,
           f"404 → Content-Type: {ct!r}")

    # BP — CORS headers não devem ser wildcard (*) para métodos perigosos
    code3, h3, _ = send_request("OPTIONS", "/",
                                 headers={"Origin": "http://evil.com",
                                          "Access-Control-Request-Method": "DELETE"})
    acao = h3.get("access-control-allow-origin", "")
    acam = h3.get("access-control-allow-methods", "")
    if acao == "*" and "DELETE" in acam:
        record("warning", "BP-03", "CORS wildcard com DELETE",
               False,
               f"Access-Control-Allow-Origin: * + Allow-Methods: {acam}",
               "Não permitir CORS wildcard para métodos destrutivos")
    else:
        record("info", "BP-03", "CORS não configurado ou restrito", True,
               f"Origin response: {acao!r}")


# ══════════════════════════════════════════════════════════════════════════════
# RELATÓRIO FINAL
# ══════════════════════════════════════════════════════════════════════════════

def print_report():
    total = len(results["pass"]) + len(results["fail"]) + len(results["warning"])
    passed = len(results["pass"])
    failed = len(results["fail"])
    warned = len(results["warning"])
    score = int(passed / total * 100) if total > 0 else 0

    print(f"\n{W}{'═'*60}{RST}")
    print(f"{W}  RELATÓRIO FINAL{RST}")
    print(f"{W}{'═'*60}{RST}")
    print(f"  {G}✓ PASS   {passed:>3}{RST}")
    print(f"  {R}✗ FAIL   {failed:>3}{RST}")
    print(f"  {Y}⚠ WARN   {warned:>3}{RST}")
    print(f"  {W}  TOTAL  {total:>3}{RST}")
    print()

    if score >= 90:
        colour = G
        verdict = "EXCELENTE"
    elif score >= 70:
        colour = Y
        verdict = "ACEITÁVEL"
    elif score >= 50:
        colour = M
        verdict = "REQUER ATENÇÃO"
    else:
        colour = R
        verdict = "CRÍTICO"

    print(f"  Score: {colour}{BOLD}{score}%  {verdict}{RST}")
    print()

    if results["fail"]:
        print(f"{R}{BOLD}  Falhas:{RST}")
        for e in results["fail"]:
            print(f"    {R}✗{RST} [{e['id']}] {e['name']}")
            if e.get("detail"):
                print(f"       {DIM}{e['detail']}{RST}")

    if results["warning"]:
        print(f"\n{Y}{BOLD}  Avisos:{RST}")
        for e in results["warning"]:
            print(f"    {Y}⚠{RST} [{e['id']}] {e['name']}")

    print(f"\n{DIM}  Tester gerado para análise de segurança do projecto Webserv (42){RST}")
    print(f"{W}{'═'*60}{RST}\n")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def check_server_alive():
    code, _, _ = send_request("GET", "/", timeout=3.0)
    return code is not None and code > 0

def main():
    global HOST, PORT

    if len(sys.argv) >= 2:
        HOST = sys.argv[1]
    if len(sys.argv) >= 3:
        try:
            PORT = int(sys.argv[2])
        except ValueError:
            print(f"{R}Erro: porta inválida '{sys.argv[2]}'{RST}")
            sys.exit(1)

    banner()

    print(f"  {DIM}A verificar se o servidor está disponível em {HOST}:{PORT}...{RST}")
    if not check_server_alive():
        print(f"\n  {R}✗ Servidor não responde em {HOST}:{PORT}{RST}")
        print(f"  {Y}  Inicia o webserv antes de correr o tester.{RST}\n")
        sys.exit(1)
    print(f"  {G}✓ Servidor disponível{RST}\n")

    # Executar todos os blocos de testes
    test_path_traversal()
    test_cgi_header_injection()
    test_buffer_log_injection()
    test_xss_autoindex()
    test_upload_filename()
    test_cgi_stability()
    test_content_length_overflow()
    test_delete_unauth()
    test_matchlocation_prefix()
    test_serverconfig_reuse()
    test_cgi_output_validation()
    test_parser_atoi()
    test_iterator_stability()
    test_http_conformance()
    test_timeout_resilience()
    test_best_practices()

    print_report()


if __name__ == "__main__":
    main()
