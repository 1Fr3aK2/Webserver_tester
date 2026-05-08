#!/bin/bash

HOST=127.0.0.1
PORT=8080

echo "===== FULL SECURITY & STRESS TEST ====="

########################################
# CHUNKED ATTACK
########################################
echo "[*] Chunked malformed attack"
printf "POST / HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nHELLO\r\n" | nc $HOST $PORT

########################################
# MULTIPLE MALFORMED REQUESTS
########################################
echo "[*] Malformed spam"
for i in {1..20}; do
    echo -e "BADREQUEST\r\n\r\n" | nc $HOST $PORT &
done
wait

########################################
# CGI DOS
########################################
echo "[*] CGI DoS test"
for i in {1..20}; do
    echo -e "GET /slow.sh HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT &
done
wait

########################################
# SLOWLORIS (partial request)
########################################
echo "[*] Slowloris simulation"
{
sleep 2
echo -ne "GET / HTTP/1.1\r\n"
sleep 2
echo -ne "Host: localhost\r\n"
sleep 5
echo -ne "\r\n"
} | nc $HOST $PORT

########################################
# LARGE BODY FLOOD
########################################
echo "[*] Large body flood"
for i in {1..10}; do
    perl -e 'print "POST / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 5000\r\n\r\n"; print "A"x5000;' | nc $HOST $PORT &
done
wait

########################################
# HEADER CASE BYPASS
########################################
echo "[*] Header case test"
printf "GET / HTTP/1.1\r\nhost: localhost\r\n\r\n" | nc $HOST $PORT

########################################
# CONNECTION FLOOD
########################################
echo "[*] Connection flood"
for i in {1..200}; do
    echo -e "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc $HOST $PORT &
done
wait

########################################
# PIPELINE ABUSE
########################################
echo "[*] Pipeline abuse"
(
for i in {1..20}; do
    echo -ne "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
done
) | nc $HOST $PORT

########################################
# RANDOM FUZZING
########################################
echo "[*] Fuzzing"
for i in {1..50}; do
    head -c 100 /dev/urandom | nc $HOST $PORT &
done
wait

echo "===== TEST COMPLETE ====="
