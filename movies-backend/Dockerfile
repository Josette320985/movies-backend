FROM python:3.11-slim

# Instalar nginx, fail2ban y dependencias
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    fail2ban \
    iptables \
    iproute2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar la app
COPY main.py .

# Configuracion de nginx (reverse proxy a uvicorn)
COPY nginx.conf /etc/nginx/sites-available/default
RUN rm -f /etc/nginx/sites-enabled/default && ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Configuracion de fail2ban
COPY fail2ban/jail.local /etc/fail2ban/jail.local
COPY fail2ban/filter-http-flood.conf /etc/fail2ban/filter.d/http-flood.conf
COPY fail2ban/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]