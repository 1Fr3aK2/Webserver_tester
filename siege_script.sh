#!/bin/bash

URL="http://localhost:8080"

RESULTS="results"
TMP="$RESULTS/tmp"
LOG="$RESULTS/webserv_eval.log"

mkdir -p "$RESULTS"
mkdir -p "$TMP"

PASS=0
FAIL=0

echo "========================================" | tee "$LOG"
echo "🔥 42 WEBSERV FULL AUTOMATED EVALUATOR" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

# =====================================================
# UTILS
# =====================================================

run_test() {
    NAME="$1"
    CMD="$2"
    EXPECT="$3"

    echo ""
    echo "🧪 TEST: $NAME" | tee -a "$LOG"
    echo "➡️ CMD: $CMD" | tee -a "$LOG"

    OUTPUT=$(eval "$CMD" 2>/dev/null)

    echo "$OUTPUT" > "$RESULTS/$NAME.txt"

    if echo "$OUTPUT" | grep -Eq "$EXPECT"; then
        echo "✅ PASS ($EXPECT found)" | tee -a "$LOG"
        PASS=$((PASS+1))
    else
        echo "❌ FAIL ($EXPECT not found)" | tee -a "$LOG"
        FAIL=$((FAIL+1))
    fi
}

# Helper para verificar resultados do siege
# O siege usa TABs no resumo, não espaços — usar .* para cobrir ambos
check_siege() {
    FILE="$1"
    LABEL="$2"

    # Remove códigos de cor ANSI antes de fazer grep
    CLEAN=$(sed 's/\x1b\[[0-9;]*m//g' "$FILE")

    if echo "$CLEAN" | grep -qP "Failed transactions:.*\b0$"; then
        echo "✅ $LABEL PASS" | tee -a "$LOG"
        PASS=$((PASS+1))
    else
        FAILED=$(echo "$CLEAN" | grep "Failed transactions:" | tail -1)
        echo "❌ $LABEL FAIL ($FAILED)" | tee -a "$LOG"
        FAIL=$((FAIL+1))
    fi
}

# =====================================================
# 1. BASIC ROUTES
# =====================================================

run_test "root_route" \
"curl -i '$URL/'" \
"200 OK"

run_test "index_route" \
"curl -i '$URL/index.html'" \
"200 OK"

# =====================================================
# 2. ROUTING EDGE CASES
# =====================================================

EDGE_URLS=(
"$URL//"
"$URL/./"
"$URL/test"
"$URL/test/"
"$URL/images"
"$URL/images/"
"$URL/test/./"
"$URL/images/./"
)

for u in "${EDGE_URLS[@]}"; do
    NAME=$(echo "$u" | tr '/:' '_')
    run_test "$NAME" \
    "curl -i '$u'" \
    "HTTP/1.1"
done

# =====================================================
# 3. PATH TRAVERSAL
# =====================================================

run_test "path_traversal_root" \
"curl -i '$URL/../'" \
"200"

run_test "path_traversal_test" \
"curl -i '$URL/test/../'" \
"200"

# =====================================================
# 4. QUERY STRINGS
# =====================================================

run_test "query_string_normal" \
"curl -i '$URL/?a=1&b=2'" \
"200 OK"

LONG_QUERY=$(python3 -c "print('a'*2000)")

run_test "query_string_huge" \
"curl -i '$URL/?$LONG_QUERY'" \
"414|400|431|200"

# =====================================================
# 5. ENCODING
# =====================================================

run_test "encoding_space" \
"curl -i '$URL/%20'" \
"400|404"

run_test "encoding_traversal" \
"curl -i '$URL/%2e%2e%2f'" \
"403|404"

# =====================================================
# 6. ERROR HANDLING
# =====================================================

run_test "404_test" \
"curl -i '$URL/does_not_exist'" \
"404"

run_test "403_test" \
"curl -i '$URL/forbidden/'" \
"403"

# =====================================================
# 7. REDIRECT
# =====================================================

run_test "redirect_test" \
"curl -i '$URL/redir/'" \
"301"

# =====================================================
# 8. UPLOAD TESTS (ALL INSIDE results/tmp)
# =====================================================

echo "hello webserv" > "$TMP/tmp.txt"

run_test "upload_small" \
"curl -i -X POST --data-binary @$TMP/tmp.txt '$URL/upload/'" \
"200|201"

python3 -c "print('A'*5000)" > "$TMP/big.txt"

run_test "upload_big" \
"curl -i -X POST --data-binary @$TMP/big.txt '$URL/upload/'" \
"413"

# =====================================================
# 9. CGI
# =====================================================

run_test "cgi_python_get" \
"curl -i '$URL/cgi-bin/test.py'" \
"200"

run_test "cgi_python_post" \
"curl -i -X POST -d 'a=1' '$URL/cgi-bin/test.py'" \
"200"

run_test "cgi_bash" \
"curl -i '$URL/cgi-bin/test.sh'" \
"200"

# =====================================================
# 10. FUZZING
# =====================================================

echo "🔥 FUZZING URLS" | tee -a "$LOG"

FUZZ_FAIL=0

for i in {1..50}; do
    RAND_PATH=$(head /dev/urandom | tr -dc A-Za-z0-9/_ | head -c 30)

    CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL/$RAND_PATH")

    echo "$RAND_PATH -> $CODE" >> "$RESULTS/fuzz.txt"

    if [[ "$CODE" == "500" || "$CODE" == "502" || "$CODE" == "504" ]]; then
        FUZZ_FAIL=$((FUZZ_FAIL+1))
    fi
done

if [ "$FUZZ_FAIL" -gt 0 ]; then
    echo "❌ FUZZ FAIL ($FUZZ_FAIL)" | tee -a "$LOG"
    FAIL=$((FAIL+1))
else
    echo "✅ FUZZ OK" | tee -a "$LOG"
    PASS=$((PASS+1))
fi

# =====================================================
# 11. SIEGE
# =====================================================

echo "💣 SIEGE LIGHT" | tee -a "$LOG"
siege -c50 -t15S "$URL/" > "$RESULTS/siege_light.txt" 2>&1
check_siege "$RESULTS/siege_light.txt" "SIEGE LIGHT"

echo "💣 SIEGE MEDIUM" | tee -a "$LOG"
siege -c100 -t20S "$URL/" > "$RESULTS/siege_medium.txt" 2>&1
check_siege "$RESULTS/siege_medium.txt" "SIEGE MEDIUM"

# =====================================================
# PIPELINING
# =====================================================

echo "🧪 PIPELINING TEST" | tee -a "$LOG"

(
printf "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
printf "GET /test/ HTTP/1.1\r\nHost: localhost\r\n\r\n"
) | nc localhost 8080 > "$RESULTS/pipeline.txt"

if grep -q "HTTP/1.1" "$RESULTS/pipeline.txt"; then
    echo "✅ PIPELINING OK" | tee -a "$LOG"
    PASS=$((PASS+1))
else
    echo "❌ PIPELINING FAIL" | tee -a "$LOG"
    FAIL=$((FAIL+1))
fi

# =====================================================
# FINAL SCORE
# =====================================================

TOTAL=$((PASS+FAIL))

echo ""
echo "========================================" | tee -a "$LOG"
echo "🏁 FINAL RESULTS" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

echo "✅ PASSED: $PASS" | tee -a "$LOG"
echo "❌ FAILED: $FAIL" | tee -a "$LOG"

SCORE=$((PASS * 100 / TOTAL))

echo "🎯 SCORE: $SCORE / 100" | tee -a "$LOG"

echo "========================================" | tee -a "$LOG"
echo "📁 ALL RESULTS IN: $RESULTS/" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
