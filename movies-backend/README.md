# Movies Backend — FastAPI + Nginx + Fail2Ban

API REST del proyecto **CineLog** — gestiona películas con autenticación **OAuth 2.0 / OIDC** validando **JWT** emitidos por **Keycloak**, protegida con **Fail2Ban**.

![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-1.27-009639?logo=nginx&logoColor=white)
![Fail2Ban](https://img.shields.io/badge/Fail2Ban-1.0-EE0000?logo=linux&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Debian-2496ED?logo=docker&logoColor=white)

---

##  Description

Backend en **FastAPI** que:

- ✅ Valida **JWT** (RS256) emitidos por **Keycloak** contra su clave pública (JWKS)
- ✅ Expone endpoints protegidos con **Bearer Token**
- ✅ Hace **CORS** para el frontend Vue (`:5173`)
- ✅ Se sirve detrás de **Nginx** (reverse proxy) con **Fail2Ban** en producción
- ✅ Se despliega como imagen **Docker**

---

##  Repositorios Relacionados

| # | Repositorio | Descripción |
|---|---|---|
| 1 | [ldap-keycloak-oauth2-lab](https://github.com/Josette320985/ldap-keycloak-oauth2-lab) | Infraestructura Docker (OpenLDAP + Keycloak + PostgreSQL) |
| 2 | **movies-backend** (este repo) | API FastAPI con validación JWT |
| 3 | [movies-dashboard](https://github.com/Josette320985/movies-dashboard) | Frontend Vue.js con Pinia |
| 4 | [ddos-script](https://github.com/Josette320985/ddos-script) | Script de load test |

---

##  Endpoints

| Método | Endpoint | Descripción | Requiere JWT |
|---|---|---|---|
| GET | `/health` | Estado del servidor | ❌ |
| GET | `/docs` | Swagger UI | ❌ |
| GET | `/api/movies` | Listar todas las películas | ✅ |
| POST | `/api/movies` | Agregar una película nueva | ✅ |

> ⚠️ **Nota:** El endpoint raíz `/` no existe (devuelve `404 Not Found`). Usa `/health` o `/docs`.

---

##  Cómo levantar el contenedor

### Requisitos previos

- **Docker Desktop** instalado y corriendo.
- La infraestructura **Keycloak + LDAP** debe estar levantada primero:
  - `ldap-keycloak-oauth2-lab` (en `http://localhost:8081`)

### Paso 1: Levantar la infraestructura

```bash
# Terminal 1: Infraestructura (LDAP + Keycloak)
cd ldap-keycloak-oauth2-lab
docker compose up -d
```

**Espera 30 segundos** a que Keycloak termine de arrancar.

**Verifica que esté corriendo:**
```bash
docker ps | grep keycloak
```

### Paso 2: Levantar el backend

```bash
# Terminal 2: Backend
cd movies-backend
docker compose up -d --build
```

**Tiempo esperado:** 1-2 minutos.

**Salida esperada:**
```
[+] Building XXs (XX/XX) FINISHED
 => naming to docker.io/library/movies-backend-backend
[+] Running 1/1
 ✔ Container movies-backend  Started
```

### Paso 3: Verificar que funciona

Abre en el navegador:

| URL | Debe devolver |
|---|---|
| **http://localhost:8001/health** | `{"status":"ok"}` |
| http://localhost:8001/docs | Swagger UI |

### Paso 4: Verificar que Fail2Ban está activo

```bash
docker exec movies-backend fail2ban-client status
docker exec movies-backend fail2ban-client status http-flood
```

**Esperado:**
```
Status for the jail: http-flood
|- Filter
|  |- Currently failed: 0
|  `- File list:        /var/log/nginx/access.log
`- Actions
   |- Currently banned: 0
   `- Banned IP list:
```

---

##  Cómo detener el contenedor

```bash
cd movies-backend
docker compose down
```

**Para detener TODOS los servicios del proyecto:**

```bash
# Detener frontend
cd movies-dashboard && docker compose down

# Detener backend
cd movies-backend && docker compose down

# Detener infraestructura
cd ldap-keycloak-oauth2-lab && docker compose down
```

---

##  Estructura del Proyecto

```
movies-backend/
├── main.py                        # Código FastAPI
├── requirements.txt               # Dependencias Python
├── fail2ban/
│   ├── jail.local                 # Jail http-flood
│   ├── filter-http-flood.conf
│   └── entrypoint.sh              # Arranca uvicorn + nginx + fail2ban
├── Dockerfile                     # Python + Nginx + Fail2Ban
├── nginx.conf                     # Reverse proxy a uvicorn:8000
├── docker-compose.yml
├── .dockerignore
└── README.md
```

---

##  Fail2Ban Configuration

**Jail `http-flood`:** banea IPs que envían **+60 requests en 10 segundos**.

**`fail2ban/jail.local`:**
```ini
[DEFAULT]
banaction = iptables-allports
ignoreip = 127.0.0.1/8
usedns = no
backend = polling
bantime = 10m
bantime.increment = true
bantime.factor = 2
bantime.maxtime = 1d

[http-flood]
enabled = true
port = http,https
filter = http-flood
logpath = /var/log/nginx/access.log
maxretry = 60
findtime = 10s
```

**Filtro `fail2ban/filter-http-flood.conf`:**
```ini
[Definition]
failregex = ^<HOST> -.*"(?:GET|POST|HEAD|PUT|DELETE|PATCH|OPTIONS|CONNECT|TRACE) [^"]*" [0-9]{3}
ignoreregex =
```

**Arquitectura interna:**
```
Cliente → Nginx (:80) → Uvicorn (:8000) → FastAPI
            │
            └── Fail2Ban monitorea /var/log/nginx/access.log
```

---

##  Load Test Results

**RPS máximo seguro desde una IP:** **5 RPS**

| RPS | Path | Total | OK | Failed | % Failed | ¿Baneó? |
|---|---|---|---|---|---|---|
| **5** | `/health` | 98 | 98 | 0 | **0%** | ❌ NO |
| 6 | `/health` | 117 | 63 | 54 | 46% | ✅ SÍ |

Ver detalles completos en el [repo ddos-script](https://github.com/Josette320985/ddos-script).

---

##  Probar Fail2Ban manualmente

```bash
# Enviar 200 requests rápidos al endpoint /health (PowerShell)
1..200 | ForEach-Object {
    try { Invoke-WebRequest -Uri http://localhost:8001/health -UseBasicParsing | Out-Null } catch { }
}

# Ver si tu IP fue baneada
docker exec movies-backend fail2ban-client status http-flood

# Desbanear
docker exec movies-backend fail2ban-client set http-flood unbanip <IP>
```

---

##  Validación del JWT

El backend valida el JWT usando:

- **ISSUER:** `http://localhost:8081/realms/cybersecurity`
- **JWKS_URL:** `http://keycloak-proxy:80/realms/cybersecurity/protocol/openid-connect/certs` (red interna Docker)
- **AUDIENCE:** `fastapi-api`
- **Algoritmo:** `RS256`

Si el token es inválido, expirado o tiene audience incorrecta → **401 Unauthorized**.

**Ejemplo con curl:**

```bash
# 1. Obtener JWT de Keycloak
TOKEN=$(curl -s -X POST http://localhost:8081/realms/cybersecurity/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=fastapi-api" \
  -d "username=alice" \
  -d "password=alice123" \
  -d "scope=openid" | jq -r '.access_token')

# 2. Usar el JWT para llamar al backend
curl http://localhost:8001/api/movies \
  -H "Authorization: Bearer $TOKEN"
```

---

##  Troubleshooting

| Problema | Solución |
|---|---|
| `{"detail":"Not Found"}` en `/` | **Normal.** Usa `/health` o `/docs`. |
| `401 Unauthorized` en `/api/movies` | El JWT es inválido o expirado. Verifica que Keycloak esté corriendo. |
| `All connection attempts failed` en logs | El backend no puede alcanzar Keycloak. Verifica la red Docker `auth-network`. |
| Fail2Ban banea tu IP durante pruebas | `docker exec movies-backend fail2ban-client set http-flood unbanip <IP>` |
| El contenedor no arranca | `docker logs movies-backend` |
| Error de CORS en el frontend | Verifica `allow_origins=["*"]` en `main.py` |

---

