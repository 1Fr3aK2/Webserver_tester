#!/bin/bash
# test_receive.sh — versão com curl e netcat

HOST="127.0.0.1"
PORT="8080"

echo "=== TESTE 1: Header grande (curl) ==="
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "X-Padding: $(python3 -c 'print("A"*1100)')" \
  http://$HOST:$PORT/index.html

echo ""
echo "=== TESTE 2: POST fragmentado (netcat) ==="
# Envia header e body com pausa entre eles
{
  printf "POST /upload HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5\r\n\r\n"
  sleep 0.2
  printf "hello"
} | nc -q 2 $HOST $PORT

echo ""
echo "=== TESTE 3: Body de 1025 bytes (curl) ==="
curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST \
  -H "Content-Type: text/plain" \
  --data "$(python3 -c 'print("A"*1025, end="")')" \
  http://$HOST:$PORT/upload

echo ""
echo "=== TESTE 4: Stress — 50 requests grandes em paralelo ==="
for i in $(seq 1 50); do
  curl -s -o /dev/null \
    -H "X-Padding: $(python3 -c 'print("A"*500)')" \
    http://$HOST:$PORT/index.html &
done
wait
echo "Stress test concluído"