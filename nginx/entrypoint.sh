#!/bin/sh
# Подставляем NGINX_ADMIN_PATH в шаблон, остальные $var оставляем как есть.
# envsubst с явным списком заменяет только указанные переменные,
# $$ в шаблоне превращает в $ для nginx.
envsubst '$NGINX_ADMIN_PATH' \
    < /etc/nginx/nginx.conf.template \
    | sed 's/\$\$/$/g' \
    > /etc/nginx/nginx.conf

nginx -t && exec nginx -g 'daemon off;'
