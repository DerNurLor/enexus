#!/bin/sh
# Подставляем переменные в шаблон nginx.conf.
# Явный список через запятую — только указанные переменные заменяются,
# остальные $var в конфиге остаются как есть (nginx их использует сам).
# $$ в шаблоне → $ для nginx (sed финальный шаг).

envsubst '$NGINX_ADMIN_PATH,$NGINX_DOMAIN' \
    < /etc/nginx/nginx.conf.template \
    | sed 's/\$\$/$/g' \
    > /etc/nginx/nginx.conf

# Валидируем конфиг перед запуском
nginx -t || { echo "❌ Ошибка в nginx.conf — проверь шаблон"; exit 1; }

exec nginx -g 'daemon off;'
