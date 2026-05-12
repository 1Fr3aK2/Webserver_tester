#!/bin/bash

URL="http://localhost:8080/cgi-bin"
PASS=0
FAIL=0

# ── cores ──────────────────────────────────────────────────────────────────
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
RESET="\033[0m"

# ── helper ─────────────────────────────────────────────────────────────────
check()
{
    local NAME="$1"
    local EXPECTED="$2"
    local CMD="$3"

    echo -n "  $NAME ... "
    CODE=$(eval "$CMD" 2>/dev/null)

    if [ "$CODE" = "$EXPECTED" ]; then
        echo -e "${GREEN}PASS${RESET}  (got $CODE, expected $EXPECTED)"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}FAIL${RESET}  (got $CODE, expected $EXPECTED)"
        FAIL=$((FAIL + 1))
    fi
}

# ── criar scripts CGI ──────────────────────────────────────────────────────
setup_scripts()
{
    CGI_DIR="./www/cgi-bin"
    mkdir -p "$CGI_DIR"

    # fork_bomb.sh — deve terminar rápido e dar 200
    cat > "$CGI_DIR/fork_bomb.sh" << 'EOF'
#!/bin/bash
for i in $(seq 1 20); do
    sleep 5 &
done
echo "Content-Type: text/plain"
echo ""
echo "spawned"
EOF

    # infinite_read.sh — bloqueia em leitura → 504
    cat > "$CGI_DIR/infinite_read.sh" << 'EOF'
#!/bin/bash
while IFS= read -r -n1 char; do
    :
done
echo "Content-Type: text/plain"
echo ""
echo "done"
EOF

    # invalid.sh — output sem Content-Type → 502
    cat > "$CGI_DIR/invalid.sh" << 'EOF'
#!/bin/bash
printf "no headers at all, just body text"
EOF

    # payloadtolarge.sh — output > MAX_CGI_OUTPUT → 502
    cat > "$CGI_DIR/payloadtolarge.sh" << 'EOF'
#!/bin/bash
echo "Content-Type: text/plain"
echo ""
python3 -c "print('B' * 2000000)"
EOF

    # process_crash.py — exit(1) → 500
    cat > "$CGI_DIR/process_crash.py" << 'EOF'
#!/usr/bin/env python3
import sys
print("Content-Type: text/plain\r")
print("\r")
sys.exit(1)
EOF

    # timeout.sh — sleep 30 → 504
    cat > "$CGI_DIR/timeout.sh" << 'EOF'
#!/bin/bash
sleep 30
echo "Content-Type: text/plain"
echo ""
echo "never reached"
EOF

    # shell.sh — cat /etc/passwd sem headers → 502
    cat > "$CGI_DIR/shell.sh" << 'EOF'
#!/bin/bash
cat /etc/passwd
EOF

    chmod +x "$CGI_DIR"/*.sh "$CGI_DIR"/*.py 2>/dev/null
    echo -e "${YELLOW}[SETUP]${RESET} Scripts criados em $CGI_DIR"
}

# ── verificar que o server está up ─────────────────────────────────────────
check_server()
{
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$URL/../")
    if [ "$CODE" = "000" ]; then
        echo -e "${RED}[ERROR]${RESET} Server não está a responder em $URL"
        echo "        Inicia o server antes de correr este script."
        exit 1
    fi
    echo -e "${YELLOW}[INFO]${RESET}  Server up (got $CODE on /)"
}

# ── testes ─────────────────────────────────────────────────────────────────
run_tests()
{
    echo ""
    echo "══════════════════════════════════════════"
    echo "  CGI BEHAVIOUR TESTS"
    echo "══════════════════════════════════════════"

    # fork_bomb — script termina imediatamente, filhos ficam órfãos
    echo ""
    echo "▸ fork_bomb.sh  (esperado: 200)"
    check "fork_bomb.sh" "200" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 '$URL/fork_bomb.sh'"

    # invalid — sem Content-Type
    echo ""
    echo "▸ invalid.sh  (esperado: 502)"
    check "invalid.sh" "502" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 '$URL/invalid.sh'"

    # payloadtolarge — passa MAX_CGI_OUTPUT
    echo ""
    echo "▸ payloadtolarge.sh  (esperado: 502)"
    check "payloadtolarge.sh" "502" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 15 '$URL/payloadtolarge.sh'"

    # process_crash — exit(1)
    echo ""
    echo "▸ process_crash.py  (esperado: 500)"
    check "process_crash.py" "500" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 '$URL/process_crash.py'"

    # shell — cat /etc/passwd sem headers CGI válidos
    echo ""
    echo "▸ shell.sh  (esperado: 502)"
    check "shell.sh" "502" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 '$URL/shell.sh'"

    # timeout — sleep 30, timeout CGI (aguarda CGI_TIMEOUT_SEC + margem)
    echo ""
    echo "▸ timeout.sh  (esperado: 504)  [aguarda ~12s]"
    check "timeout.sh" "504" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 20 '$URL/timeout.sh'"

    # infinite_read — bloqueia em leitura de stdin
    echo ""
    echo "▸ infinite_read.sh via POST  (esperado: 504)  [aguarda ~12s]"
    check "infinite_read.sh" "504" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 20 -X POST -d 'hello' '$URL/infinite_read.sh'"

    # server ainda responde após todos os testes
    echo ""
    echo "▸ server still alive  (esperado: 200)"
    check "server alive" "200" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 'http://localhost:8080/'"
}

# ── resultado final ────────────────────────────────────────────────────────
summary()
{
    TOTAL=$((PASS + FAIL))
    echo ""
    echo "══════════════════════════════════════════"
    echo -e "  PASS: ${GREEN}$PASS${RESET} / $TOTAL"
    echo -e "  FAIL: ${RED}$FAIL${RESET} / $TOTAL"
    echo "══════════════════════════════════════════"
    echo ""
    if [ "$FAIL" -eq 0 ]; then
        echo -e "${GREEN}  Todos os testes passaram!${RESET}"
    else
        echo -e "${RED}  $FAIL teste(s) falharam.${RESET}"
    fi
    echo ""
}

# ── main ───────────────────────────────────────────────────────────────────
setup_scripts
check_server
run_tests
summary
