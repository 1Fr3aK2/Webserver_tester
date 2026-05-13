#!/bin/bash

# ── cores ──────────────────────────────────────────────────────────────────
GREEN="\033[32m"
YELLOW="\033[33m"
RESET="\033[0m"

echo -e "${YELLOW}[INFO]${RESET} Criando estrutura www..."

# ── criar diretórios ───────────────────────────────────────────────────────
mkdir -p \
    www/site_alpha \
    www/site_beta \
    www/site_gamma/uploads

cp -rf www/cgi-bin/ www/site_alpha/cgi-bin/
cp -rf www/cgi-bin/ www/site_beta/cgi-bin/ 

# ── criar index.html ───────────────────────────────────────────────────────
echo '<h1>SITE ALPHA — porta 8080</h1>' > www/site_alpha/index.html
echo '<h1>SITE BETA  — porta 8081</h1>' > www/site_beta/index.html
echo '<h1>SITE GAMMA — porta 8082</h1>' > www/site_gamma/index.html

echo -e "${YELLOW}[INFO]${RESET} Criando test_ports.conf..."

# ── criar test_ports.conf ──────────────────────────────────────────────────
cat > test_ports.conf << 'EOF'
server
{
    listen 8080;
    server_name site_alpha;
    root ./www/site_alpha;
    index index.html;
    client_max_body_size 1048576;

    mime_types
    {
        text/html html htm;
        text/css css;
        application/javascript js;
        application/json json;
        image/png png;
        image/jpeg jpg jpeg;
        image/gif gif;
        image/x-icon ico;
        image/svg+xml svg;
        text/plain txt;
        application/pdf pdf;
        application/zip zip;
        application/xml xml;
        video/mp4 mp4;
        audio/mpeg mp3;
    }

    error_page 404 /error_pages/404.html;
    error_page 500 /error_pages/500.html;

    location /
    {
        allowed_methods GET;
        autoindex off;
    }

    location /cgi-bin/
    {
        root ./www/site_alpha/cgi-bin;
        cgi_pass on;
        cgi_ext .sh .py;

        cgi_types
        {
            .sh /bin/bash;
            .py /usr/bin/python3;
        }

        allowed_methods GET POST;
    }
}

server
{
    listen 8081;
    server_name site_beta;
    root ./www/site_beta;
    index index.html;
    client_max_body_size 1048576;

    mime_types
    {
        text/html html htm;
        text/css css;
        application/javascript js;
        application/json json;
        image/png png;
        image/jpeg jpg jpeg;
        image/gif gif;
        image/x-icon ico;
        image/svg+xml svg;
        text/plain txt;
        application/pdf pdf;
        application/zip zip;
        application/xml xml;
        video/mp4 mp4;
        audio/mpeg mp3;
    }

    error_page 404 /error_pages/404.html;
    error_page 500 /error_pages/500.html;

    location /
    {
        allowed_methods GET;
        autoindex off;
    }
}

server
{
    listen 8082;
    server_name site_gamma;
    root ./www/site_gamma;
    index index.html;
    client_max_body_size 1048576;

    mime_types
    {
        text/html html htm;
        text/css css;
        application/javascript js;
        application/json json;
        image/png png;
        image/jpeg jpg jpeg;
        image/gif gif;
        image/x-icon ico;
        image/svg+xml svg;
        text/plain txt;
        application/pdf pdf;
        application/zip zip;
        application/xml xml;
        video/mp4 mp4;
        audio/mpeg mp3;
    }

    error_page 404 /error_pages/404.html;
    error_page 500 /error_pages/500.html;

    location /
    {
        allowed_methods GET POST DELETE;
        autoindex on;
    }

    location /upload/
    {
        allowed_methods POST;
        upload_store ./www/site_gamma/uploads;
    }
}
EOF

echo -e "${YELLOW}[INFO]${RESET} Criando duplicate_port.conf..."

# ── criar duplicate_port.conf ──────────────────────────────────────────────
cat > duplicate_port.conf << 'EOF'
server
{
    listen 8080;
    server_name primeiro;
    root ./www/site_alpha;
    index index.html;
    client_max_body_size 1048576;

    mime_types
    {
        text/html html htm;
        text/css css;
        application/javascript js;
        application/json json;
        image/png png;
        image/jpeg jpg jpeg;
        image/gif gif;
        image/x-icon ico;
        image/svg+xml svg;
        text/plain txt;
        application/pdf pdf;
        application/zip zip;
        application/xml xml;
        video/mp4 mp4;
        audio/mpeg mp3;
    }

    location /
    {
        allowed_methods GET;
    }
}

server
{
    listen 8080;
    server_name segundo;
    root ./www/site_beta;
    index index.html;
    client_max_body_size 1048576;

    mime_types
    {
        text/html html htm;
        text/css css;
        application/javascript js;
        application/json json;
        image/png png;
        image/jpeg jpg jpeg;
        image/gif gif;
        image/x-icon ico;
        image/svg+xml svg;
        text/plain txt;
        application/pdf pdf;
        application/zip zip;
        application/xml xml;
        video/mp4 mp4;
        audio/mpeg mp3;
    }

    location /
    {
        allowed_methods GET;
    }
}
EOF

echo ""
echo -e "${GREEN}[OK]${RESET} Estrutura criada com sucesso!"
echo ""
echo "Arquivos criados:"
echo "  - test_ports.conf"
echo "  - duplicate_port.conf"
echo ""
