#!/bin/bash

mkdir -p YoupiBanane/nop
mkdir -p YoupiBanane/Yeah

touch YoupiBanane/youpi.bad_extension
touch YoupiBanane/youpi.bla

touch YoupiBanane/nop/youpi.bad_extension
touch YoupiBanane/nop/other.pouic

touch YoupiBanane/Yeah/not_happy.bad_extension

cat > tester.conf << EOF
server
{
    listen 8080;

    server_name localhost;

    root ./www;

    index index.html;

    client_max_body_size 4096;

    error_page 200 /error_pages/200.html;
    error_page 201 /error_pages/201.html;
    error_page 204 /error_pages/204.html;
    error_page 301 /error_pages/301.html;
    error_page 302 /error_pages/302.html;
    error_page 400 /error_pages/400.html;
    error_page 403 /error_pages/403.html;
    error_page 404 /error_pages/404.html;
    error_page 405 /error_pages/405.html;
    error_page 408 /error_pages/408.html;
    error_page 409 /error_pages/409.html;
    error_page 413 /error_pages/413.html;
    error_page 431 /error_pages/431.html;
    error_page 500 /error_pages/500.html;
    error_page 501 /error_pages/501.html;
    error_page 502 /error_pages/502.html;
    error_page 503 /error_pages/503.html;
    error_page 504 /error_pages/504.html;
    error_page 505 /error_pages/505.html;

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

    # / must answer to GET request ONLY
    location /
    {
        allowed_methods GET;
        autoindex off;
    }

    # Any file with .bla extension must answer to POST
    # request by calling the cgi_test executable
    location /bla_cgi/
    {
        cgi_pass on;
        cgi_ext .bla;

        cgi_types
        {
            .bla ./cgi_test;
        }

        allowed_methods POST;
        autoindex off;
    }

    # /post_body must answer anything to POST request
    # with a maxBody of 100
    location /post_body
    {
        allowed_methods POST;
        client_max_body_size 100;
    }

    # /directory/ must answer to GET request
    # root = YoupiBanane
    # default file = youpi.bad_extension
    location /directory/
    {
        allowed_methods GET;
        root ./YoupiBanane;
        index youpi.bad_extension;
        autoindex off;
    }
}
EOF 


echo "Everything up to work"
