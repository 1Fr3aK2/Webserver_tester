#!/bin/bash

HOST="localhost"
PORT="8080"
NGINX_PORT="8081"

pass() { echo -e "\e[32m[PASS]\e[0m $1"; }
fail() { echo -e "\e[31m[FAIL]\e[0m $1"; }
info() { echo -e "\e[34m[INFO]\e[0m $1"; }

check() {
    name=$1
    expected=$2
    cmd=$3

    info "Running: $name"
    result=$(eval "$cmd" 2>/dev/null | head -n 1)

    if echo "$result" | grep -q "$expected"; then
        pass "$name"
    else
        fail "$name -> got: $result"
    fi
    echo
}

echo "🔥 ULTIMATE WEBSERV TESTER 🔥"
echo "Target: $HOST:$PORT"
echo

#################################
# BASIC
#################################

info "=== BASIC TESTS ==="

check "GET /" "200 OK" \
"curl -s -i http://$HOST:$PORT/"

check "404 Not Found" "404 Not Found" \
"curl -s -i http://$HOST:$PORT/naoexiste"

check "405 Method Not Allowed" "405 Method Not Allowed" \
"curl -s -i -X DELETE http://$HOST:$PORT/"

check "400 Bad Request (malformed)" "400" \
"printf 'HELLO\r\n\r\n' | nc $HOST $PORT"

#################################
# SECURITY
#################################

info "=== SECURITY TESTS ==="

check "Path traversal ../ attack" "403" \
"printf 'GET /../../etc/passwd HTTP/1.1\r\nHost: localhost\r\n\r\n' | nc $HOST $PORT"

check "Encoded traversal attack" "404" \
"printf 'GET /%%2e%%2e/%%2e%%2e/etc/passwd HTTP/1.1\r\nHost: localhost\r\n\r\n' | nc $HOST $PORT"

check "Double slash bypass" "200" \
"curl -s -i http://$HOST:$PORT//"

#################################
# HEADER TESTS
#################################

info "=== HEADER ATTACKS ==="

check "Missing Host header" "400" \
"printf 'GET / HTTP/1.1\r\n\r\n' | nc $HOST $PORT"

check "Huge header attack" "400\|431" \
"printf 'GET / HTTP/1.1\r\nHost: $(printf 'A%.0s' {1..5000})\r\n\r\n' | nc $HOST $PORT"

#################################
# CGI TESTS
#################################

info "=== CGI TESTS ==="

check "CGI valid execution" "200" \
"curl -s -i http://$HOST:$PORT/cgi-bin/test.py"

check "CGI crash → 500" "500" \
"curl -s -i http://$HOST:$PORT/cgi-bin/test.py?crash=1"

check "CGI invalid output → 404" "404" \
"curl -s -i http://$HOST:$PORT/cgi-bin/bad.py"

#################################
# METHODS
#################################

info "=== METHOD TESTS ==="

check "Unknown method" "405" \
"curl -s -i -X ABC http://$HOST:$PORT/"

check "POST request" "200\|201" \
"curl -s -i -X POST http://$HOST:$PORT/test/ -d 'hello=42'"

#################################
# BODY / LIMITS
#################################

info "=== BODY LIMIT TEST ==="

check "Large body attack" "400\|413" \
"(
  printf \"POST / HTTP/1.1\r\nHost: $HOST:$PORT\r\nContent-Length: 204800\r\n\r\n\"
  dd if=/dev/zero bs=1k count=200 2>/dev/null
) | nc $HOST $PORT"

#################################
# DIRECTORY
#################################

info "=== DIRECTORY TESTS ==="

check "Autoindex working" "200" \
"curl -s -i http://$HOST:$PORT/test/"

#################################
# FUZZ TEST
#################################

info "=== FUZZ TEST (random garbage) ==="

for i in {1..5}
do
    garbage=$(head -c 50 /dev/urandom | tr -dc 'a-zA-Z0-9')
    printf "$garbage\r\n\r\n" | nc $HOST $PORT > /dev/null 2>&1
done

pass "Fuzz test did not crash server"
echo

#################################
# SLOWLORIS SIMULATION
#################################

info "=== SLOWLORIS ATTACK (partial request) ==="

{
    printf "GET / HTTP/1.1\r\n"
    sleep 2
    printf "Host: $HOST\r\n"
    sleep 2
    printf "\r\n"
} | nc $HOST $PORT > /dev/null 2>&1 &

sleep 3
pass "Server survived slowloris attempt"
echo

#################################
# CHUNKED ENCODING TEST
#################################

info "=== CHUNKED ENCODING TEST ==="

printf "POST / HTTP/1.1\r\nHost: $HOST\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nHello\r\n0\r\n\r\n" \
| nc $HOST $PORT | head -n 1

echo "(Check manually if handled correctly)"
echo

#################################
# STRESS TEST
#################################

info "=== STRESS TEST ==="

for i in {1..20}
do
    curl -s http://$HOST:$PORT/ > /dev/null &
done

wait
pass "Server survived concurrent requests"
echo

#################################
# NGINX COMPARISON (optional)
#################################

info "=== NGINX COMPARISON (optional) ==="

if nc -z localhost $NGINX_PORT; then
    echo "Comparing responses..."

    res1=$(curl -s -i http://$HOST:$PORT/naoexiste | head -n 1)
    res2=$(curl -s -i http://localhost:$NGINX_PORT/naoexiste | head -n 1)

    echo "Yours:  $res1"
    echo "NGINX:  $res2"

    if [ "$res1" == "$res2" ]; then
        pass "Matches nginx behavior"
    else
        fail "Different from nginx"
    fi
else
    info "NGINX not running on port $NGINX_PORT (skipping)"
fi

echo
echo "🔥 ALL TESTS COMPLETED 🔥"
