#!/bin/bash

# test_ports.sh
# Testa múltiplas portas, porta duplicada, e comportamento básico

URL_ALPHA="http://localhost:8080"
URL_BETA="http://localhost:8081"
URL_GAMMA="http://localhost:8082"

GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
RESET="\033[0m"

PASS=0
FAIL=0

check()
{
    local NAME="$1"
    local EXPECTED="$2"
    local CMD="$3"

    echo -n "  $NAME ... "
    CODE=$(eval "$CMD" 2>/dev/null)
    if [ "$CODE" = "$EXPECTED" ]; then
        echo -e "${GREEN}PASS${RESET}  (got $CODE)"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}FAIL${RESET}  (got $CODE, expected $EXPECTED)"
        FAIL=$((FAIL + 1))
    fi
}

check_body()
{
    local NAME="$1"
    local EXPECTED="$2"
    local CMD="$3"

    echo -n "  $NAME ... "
    BODY=$(eval "$CMD" 2>/dev/null)
    if echo "$BODY" | grep -q "$EXPECTED"; then
        echo -e "${GREEN}PASS${RESET}  (encontrou '$EXPECTED')"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}FAIL${RESET}  (não encontrou '$EXPECTED')"
        echo "    body: $BODY"
        FAIL=$((FAIL + 1))
    fi
}

# ── verificar server ───────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[SETUP]${RESET} A verificar se o servidor está online..."
for PORT in 8080 8081 8082; do
    CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 \
        "http://localhost:$PORT/")
    if [ "$CODE" = "000" ]; then
        echo -e "${RED}[ERROR]${RESET} Servidor não responde na porta $PORT"
        echo "        Lança './webserv test_ports.conf' antes de correr este script."
        exit 1
    fi
done
echo -e "${YELLOW}[INFO]${RESET}  Servidor online nas portas 8080, 8081, 8082"

# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "  TESTE 1 — Portas diferentes, sites diferentes"
echo "══════════════════════════════════════════"

check "porta 8080 responde 200" "200" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_ALPHA/'"

check "porta 8081 responde 200" "200" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_BETA/'"

check "porta 8082 responde 200" "200" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_GAMMA/'"

check_body "8080 serve site_alpha" "SITE ALPHA" \
    "curl -s --max-time 3 '$URL_ALPHA/'"

check_body "8081 serve site_beta" "SITE BETA" \
    "curl -s --max-time 3 '$URL_BETA/'"

check_body "8082 serve site_gamma" "SITE GAMMA" \
    "curl -s --max-time 3 '$URL_GAMMA/'"

# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "  TESTE 2 — Isolamento entre portas"
echo "══════════════════════════════════════════"
# Ficheiro que existe no alpha mas não no beta/gamma
echo "ficheiro_exclusivo_alpha" > www/site_alpha/only_alpha.txt

check "ficheiro do alpha acessível em 8080" "200" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_ALPHA/only_alpha.txt'"

check "mesmo ficheiro NÃO acessível em 8081" "404" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_BETA/only_alpha.txt'"

check "mesmo ficheiro NÃO acessível em 8082" "404" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_GAMMA/only_alpha.txt'"

# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "  TESTE 3 — Métodos por porta"
echo "══════════════════════════════════════════"
# alpha só tem GET — POST deve dar 405
check "8080 rejeita POST (405)" "405" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 -X POST '$URL_ALPHA/'"

# gamma tem GET POST DELETE
check "8082 aceita DELETE (204 ou 404)" "404" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 -X DELETE '$URL_GAMMA/naoexiste.txt'"

# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "  TESTE 4 — 404 em cada porta"
echo "══════════════════════════════════════════"

check "8080 404 em rota inexistente" "404" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_ALPHA/naoexiste'"

check "8081 404 em rota inexistente" "404" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_BETA/naoexiste'"

check "8082 404 em rota inexistente" "404" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_GAMMA/naoexiste'"

# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "  TESTE 5 — Porta duplicada na config"
echo "══════════════════════════════════════════"
echo ""
echo -e "${YELLOW}[MANUAL]${RESET} Este teste requer reinício do servidor."
echo ""
echo "  Cria um ficheiro 'duplicate_port.conf' com dois blocos"
echo "  'server' ambos com 'listen 8080'."
echo ""
echo "  Comportamento esperado: o servidor deve recusar iniciar"
echo "  (erro no parse ou no bind) OU ignorar o duplicado silenciosamente."
echo "  NÃO deve crashar nem ficar num estado indefinido."
echo ""
echo -e "${YELLOW}[INFO]${RESET} Cria o ficheiro e corre: ./webserv duplicate_port.conf"
echo -e "${YELLOW}[INFO]${RESET} Verifica se o processo termina com erro ou se"
echo -e "        apenas uma das portas fica activa."

# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
echo "  TESTE 6 — Servidor ainda vivo após todos os testes"
echo "══════════════════════════════════════════"

check "8080 ainda responde" "200" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_ALPHA/'"

check "8081 ainda responde" "200" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_BETA/'"

check "8082 ainda responde" "200" \
    "curl -s -o /dev/null -w '%{http_code}' --max-time 3 '$URL_GAMMA/'"

# ══════════════════════════════════════════════════════════════════════════
echo ""
echo "══════════════════════════════════════════"
TOTAL=$((PASS + FAIL))
echo -e "  PASS: ${GREEN}$PASS${RESET} / $TOTAL"
echo -e "  FAIL: ${RED}$FAIL${RESET} / $TOTAL"
echo "══════════════════════════════════════════"
echo ""
if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}  Todos os testes automáticos passaram.${RESET}"
else
    echo -e "${RED}  $FAIL teste(s) falharam.${RESET}"
fi
echo ""
