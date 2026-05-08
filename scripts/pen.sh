#!/bin/bash

HOST=127.0.0.1
PORT=8080

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

function test_case() {
    echo -e "${YELLOW}Test: $1${NC}"
    RESULT=$(echo -e "$2" | nc $HOST $PORT 2>/dev/null)
    echo "$RESULT" | head -n 5

    if echo "$RESULT" | grep -q "$3"; then
        echo -e "${GREEN}PASS${NC}\n"
    else
        echo -e "${RED}FAIL${NC}\n"
    fi
}

echo "=== BASIC ==="

test_case "GET /" \
"GET / HTTP/1.1\r\nHost: test\r\n\r\n" \
"200"

echo "=== PATH TRAVERSAL ==="

test_case "Traversal ../../" \
"GET /../../etc/passwd HTTP/1.1\r\nHost: test\r\n\r\n" \
"403"

echo "=== LARGE HEADER ==="

test_case "Huge header" \
"GET / HTTP/1.1\r\nHost: test\r\nX: $(python3 -c 'print("A"*5000)')\r\n\r\n" \
"431"

echo "=== INVALID METHOD ==="

test_case "TRACE method" \
"TRACE / HTTP/1.1\r\nHost: test\r\n\r\n" \
"405"

echo "=== MALFORMED ==="

test_case "Bad request" \
"BADREQUEST\r\n\r\n" \
"400"

echo "=== SLOWLORIS ==="

(
sleep 1
echo -n "GET / HTTP/1.1\r\nHost: test\r\n"
sleep 10
) | nc $HOST $PORT

echo -e "${RED}Check if server hangs${NC}"

echo "=== CGI TEST ==="

test_case "CGI execution" \
"GET /cgi-bin/test.py HTTP/1.1\r\nHost: test\r\n\r\n" \
"200"

echo "=== HEADER INJECTION ==="

test_case "Header injection" \
"GET / HTTP/1.1\r\nHost: test\r\nX: test\r\nBadHeader\r\n\r\n" \
"400"

echo "=== DOS BODY ==="

test_case "Big body" \
"POST / HTTP/1.1\r\nHost: test\r\nContent-Length: 9999999\r\n\r\nAAAA" \
"413"

echo "=== DIRECTORY LISTING ==="

test_case "Autoindex" \
"GET /test/ HTTP/1.1\r\nHost: test\r\n\r\n" \
"200"

echo "=== XSS CHECK ==="
echo -e "${RED}Create file <script>alert(1)</script> and access it${NC}"
