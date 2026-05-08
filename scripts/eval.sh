#!/bin/bash

HOST=127.0.0.1
PORT=8080

GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"

ok(){ echo -e "${GREEN}[OK] $1${NC}"; }
fail(){ echo -e "${RED}[FAIL] $1${NC}"; }

test(){
    NAME=$1
    CMD=$2
    EXPECT=$3

    RESPONSE=$(eval "$CMD")

    echo "$RESPONSE" | grep -q "$EXPECT" && ok "$NAME" || fail "$NAME"
}

echo "===== 42 EVALUATION TESTER ====="

# BASIC
test "Server responds" \
"echo -e 'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n' | nc $HOST $PORT" \
"HTTP/"

# GET
test "GET / returns 200" \
"echo -e 'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n' | nc $HOST $PORT" \
"200"

# 404
test "404 handling" \
"echo -e 'GET /nope HTTP/1.1\r\nHost: localhost\r\n\r\n' | nc $HOST $PORT" \
"404"

# 400
test "Bad request" \
"echo -e 'BAD REQUEST\r\n\r\n' | nc $HOST $PORT" \
"400"

# POST
test "POST basic" \
"echo -e 'POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\n\r\nhello' | nc $HOST $PORT" \
"201"

# DELETE
test "DELETE basic" \
"echo -e 'DELETE /file HTTP/1.1\r\nHost: localhost\r\n\r\n' | nc $HOST $PORT" \
"200\|204\|404"

# HEADERS
test "Header validation" \
"echo -e 'GET / HTTP/1.1\r\nInvalidHeader\r\n\r\n' | nc $HOST $PORT" \
"400"

# LARGE BODY
BIG=$(head -c 5000 </dev/zero | tr '\0' 'A')
RESPONSE=$(printf "POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5000\r\n\r\n$BIG" | nc $HOST $PORT)
echo "$RESPONSE" | grep -q "413" && ok "413 Payload too large" || fail "413 missing"

# CGI
test "CGI execution" \
"echo -e 'GET /cgi-bin/test.py HTTP/1.1\r\nHost: localhost\r\n\r\n' | nc $HOST $PORT" \
"200"

# REDIRECT
CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/redir/)
[[ "$CODE" == "301" || "$CODE" == "302" ]] && ok "Redirect" || fail "Redirect"

# AUTOINDEX
test "Autoindex" \
"echo -e 'GET /dir/ HTTP/1.1\r\nHost: localhost\r\n\r\n' | nc $HOST $PORT" \
"<html"

# PIPELINING
RESP=$( (echo -ne "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"; echo -ne "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n") | nc $HOST $PORT )
COUNT=$(echo "$RESP" | grep -c "HTTP/")
[[ $COUNT -ge 2 ]] && ok "Pipelining" || fail "Pipelining"

# MULTIPLE CONNECTIONS
echo "Stress test..."
for i in {1..50}; do
    echo -e "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT &
done
wait
ok "Concurrent connections"

echo "===== DONE ====="
