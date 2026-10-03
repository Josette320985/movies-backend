#!/bin/bash
set -e

echo "[backend] Starting entrypoint..."

mkdir -p /var/log/nginx /var/run/fail2ban

rm -f /var/log/nginx/access.log /var/log/nginx/error.log
touch /var/log/nginx/access.log /var/log/nginx/error.log
touch /var/log/fail2ban.log

rm -f /var/run/fail2ban/fail2ban.sock /var/run/fail2ban/fail2ban.pid

echo "[backend] Starting uvicorn..."
cd /app
uvicorn main:app --host 127.0.0.1 --port 8000 &
UVICORN_PID=$!

sleep 3

echo "[backend] Starting nginx..."
nginx -g 'daemon off;' &
NGINX_PID=$!

sleep 2

echo "[backend] Starting fail2ban..."
fail2ban-client -x start

echo "[backend] uvicorn + nginx + fail2ban running."

wait -n $UVICORN_PID $NGINX_PID