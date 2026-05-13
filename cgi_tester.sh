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

# ── verificar que o server está up ─────────────────────────────────────────
check_server()
{
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://localhost:8080/")

    if [ "$CODE" = "000" ]; then
        echo -e "${RED}[ERROR]${RESET} Server não está a responder"
        echo "        Inicia o server antes de correr este script."
        exit 1
    fi

    echo -e "${YELLOW}[INFO]${RESET} Server up (got $CODE on /)"
}

# ── testes ─────────────────────────────────────────────────────────────────
run_tests()
{
    echo ""
    echo "══════════════════════════════════════════"
    echo "  CGI BEHAVIOUR TESTS"
    echo "══════════════════════════════════════════"

    # fork_bomb
    echo ""
    echo "▸ fork_bomb.sh  (esperado: 200)"
    check "fork_bomb.sh" "200" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 10 '$URL/fork_bomb.sh'"

    # invalid
    echo ""
    echo "▸ invalid.sh  (esperado: 502)"
    check "invalid.sh" "502" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 '$URL/invalid.sh'"

    # payload too large
    echo ""
    echo "▸ payloadtolarge.sh  (esperado: 502)"
    check "payloadtolarge.sh" "502" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 15 '$URL/payloadtolarge.sh'"

    # process crash
    echo ""
    echo "▸ process_crash.py  (esperado: 500)"
    check "process_crash.py" "500" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 '$URL/process_crash.py'"

    # shell
    echo ""
    echo "▸ shell.sh  (esperado: 502)"
    check "shell.sh" "502" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 5 '$URL/shell.sh'"

    # timeout
    echo ""
    echo "▸ timeout.sh  (esperado: 504)  [aguarda ~12s]"
    check "timeout.sh" "504" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 20 '$URL/timeout.sh'"

    # infinite read
    echo ""
    echo "▸ infinite_read.sh via POST  (esperado: 504)  [aguarda ~12s]"
    check "infinite_read.sh" "504" \
        "curl -s -o /dev/null -w '%{http_code}' --max-time 20 -X POST -d 'hello' '$URL/infinite_read.sh'"

    # server alive
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
        echo -e "${GREEN}Todos os testes passaram!${RESET}"
    else
        echo -e "${RED}$FAIL teste(s) falharam.${RESET}"
    fi

    echo ""
}

# ── main ───────────────────────────────────────────────────────────────────
check_server
run_tests
summary
