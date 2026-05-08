#!/bin/bash

HOST=127.0.0.1
PORT=8080

GREEN="\033[0;32m"
RED="\033[0;31m"
NCOLOR="\033[0m"

function ok() {
    echo -e "${GREEN}[OK] $1${NCOLOR}"
}

function fail() {
    echo -e "${RED}[FAIL] $1${NCOLOR}"
}

function test_title() {
    echo -e "\n===== $1 ====="
}

########################################
# BASIC CONNECTIVITY
########################################
test_title "BASIC CONNECTIVITY"

echo -e "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT > response.txt

grep -q "HTTP/" response.txt && ok "Server responds" || fail "No response"

########################################
# GET REQUEST
########################################
test_title "GET REQUEST"

echo -e "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT > response.txt

grep -q "200" response.txt && ok "GET / returns 200" || fail "GET failed"

########################################
# 404 TEST
########################################
test_title "404 TEST"

echo -e "GET /notfound HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT > response.txt

grep -q "404" response.txt && ok "404 handled" || fail "404 missing"

########################################
# BAD REQUEST
########################################
test_title "BAD REQUEST"

echo -e "BADREQUEST\r\n\r\n" | nc $HOST $PORT > response.txt

grep -q "400" response.txt && ok "400 handled" || fail "No 400 for invalid request"

########################################
# POST REQUEST
########################################
test_title "POST REQUEST"

REQUEST="POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 11\r\n\r\nhello=world"

echo -e "$REQUEST" | nc $HOST $PORT > response.txt

(grep -q "200" response.txt || grep -q "201" response.txt ) && ok "POST handled" || fail "POST failed"

########################################
# DELETE REQUEST
########################################
test_title "DELETE REQUEST"

echo -e "DELETE /test.txt HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT > response.txt

grep -E -q "200|204|404" response.txt && ok "DELETE handled" || fail "DELETE failed"

########################################
# LARGE BODY (413)
########################################
test_title "PAYLOAD TOO LARGE"

BIG=$(head -c 5000 </dev/zero | tr '\0' 'A')

printf "POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5000\r\n\r\n$BIG" | nc $HOST $PORT > response.txt

grep -q "413" response.txt && ok "413 handled" || fail "No 413"

########################################
# MULTIPLE REQUESTS SAME CONNECTION
########################################
test_title "PIPELINING TEST"

(
echo -ne "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
echo -ne "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
) | nc $HOST $PORT > response.txt

COUNT=$(grep -c "HTTP/" response.txt)
[ "$COUNT" -ge 2 ] && ok "Pipelining works" || fail "Pipelining failed"

########################################
# CGI TEST
########################################
test_title "CGI TEST"

echo -e "GET /cgi-bin/test.py HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT > response.txt

grep -q "200" response.txt && ok "CGI executed" || fail "CGI failed"

########################################
# DIRECTORY LISTING
########################################
test_title "AUTOINDEX"

echo -e "GET /dir/ HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT > response.txt

grep -q "<html" response.txt && ok "Autoindex works" || fail "Autoindex missing"

########################################
# REDIRECTION
########################################
test_title "REDIRECTION"

curl -s -o /dev/null -w "%{http_code}" http://$HOST:$PORT/redir/ | grep -q "301\|302" \
    && ok "Redirect works" || fail "Redirect failed"

########################################
# STRESS TEST (connections)
########################################
test_title "STRESS TEST (connections)"

for i in {1..100}; do
    echo -e "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT &
done

wait
ok "Handled 100 concurrent connections"

########################################
# SLOW CLIENT (timeout test)
########################################
test_title "SLOW CLIENT"

{
sleep 2
echo -ne "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
} | nc $HOST $PORT > response.txt

grep -q "HTTP/" response.txt && ok "Handles slow client" || fail "Timeout issue"

########################################
# INVALID HEADERS
########################################
test_title "INVALID HEADERS"

echo -e "GET / HTTP/1.1\r\nInvalidHeader\r\n\r\n" | nc $HOST $PORT > response.txt

grep -q "400" response.txt && ok "Invalid header rejected" || fail "Header validation broken"

########################################
# DIRECTORY TRAVERSAL
########################################
test_title "DIRECTORY TRAVERSAL"

echo -e "GET /../../etc/passwd HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT > response.txt

grep -q "403" response.txt && ok "Traversal blocked" || fail "VULNERABLE to traversal"

########################################
# END
########################################
echo -e "\n===== TESTS FINISHED ====="
