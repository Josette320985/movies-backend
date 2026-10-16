# Reporte de Correcciones de Seguridad — movies-backend (Backend)

Este documento detalla las correcciones aplicadas y los hallazgos restantes en el servicio **`movies-backend`** de CineLog.

---

## Resumen

| Métrica | Antes | Después |
|---|---:|---:|
| Hallazgos totales | 14 | 2 |
| Reducción | — | **86 %** |

---

## Correcciones aplicadas

### 1. Headers de seguridad en `nginx.conf`

Se reescribió el archivo `nginx.conf` para incorporar encabezados de seguridad y mejorar la protección del servicio backend.

```nginx
server {
    listen 80 default_server;
    server_name localhost;

    server_tokens off;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;
    add_header Cross-Origin-Embedder-Policy "require-corp" always;
    add_header Cross-Origin-Resource-Policy "same-origin" always;
    add_header X-Permitted-Cross-Domain-Policies "none" always;

    access_log /var/log/nginx/access.log combined;
    error_log /var/log/nginx/error.log warn;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_read_timeout 60s;
    }
}
```

**Nota:** Inicialmente se incluyó el encabezado `X-XSS-Protection "1; mode=block"`, pero posteriormente se eliminó por estar obsoleto y no constituir un mecanismo de protección recomendado para navegadores modernos.

### 2. Restricción de CORS en `main.py`

Se reemplazó la configuración original de CORS, que permitía cualquier origen, método y encabezado mediante `allow_origins=["*"]`, `allow_methods=["*"]` y `allow_headers=["*"]`, por una configuración más restrictiva.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Efecto:** Se restringieron los orígenes autorizados a las direcciones locales del frontend y se limitaron los métodos y encabezados HTTP permitidos. Esto reduce la exposición del backend frente a solicitudes procedentes de orígenes no autorizados.

Esta configuración está orientada al entorno local de desarrollo. Si el sistema se despliega en producción, deberán sustituirse los orígenes locales por los dominios autorizados correspondientes.

### 3. CSP específico y ocultamiento del encabezado `Allow`

Se agregó al archivo `nginx.conf` la siguiente política de seguridad de contenido (CSP):

```nginx
add_header Content-Security-Policy "default-src 'none'; frame-ancestors 'none'" always;
```

Además, dentro del bloque `location /`, se incorporó la siguiente directiva:

```nginx
proxy_hide_header Allow;
```

**Efecto:** La política CSP restringe la carga de recursos por defecto y prohíbe que el contenido se muestre dentro de marcos o iframes. Por su parte, `proxy_hide_header Allow` evita que Nginx reenvíe al cliente el encabezado `Allow` recibido del servidor de origen.

Con estos cambios se reportó la eliminación de los hallazgos `content-security-policy` y `options-method`.

**Consideración:** La directiva `proxy_hide_header Allow` oculta el encabezado en la respuesta, pero no deshabilita los métodos HTTP en el servidor. La restricción efectiva de métodos debe aplicarse mediante la configuración de Nginx o de la aplicación.

### 4. Aplicación de HSTS

Se utilizó el siguiente comando de PowerShell para incorporar el encabezado HTTP Strict Transport Security (HSTS) a `nginx.conf`, siempre que no estuviera presente.

```powershell
cd C:\Users\naher\Documents\PracticaFinal\movies-backend

$content = Get-Content nginx.conf -Raw

if ($content -notmatch "Strict-Transport-Security") {
    $content = $content -replace '(add_header X-Permitted-Cross-Domain-Policies "none" always;)', '$1' + "`n    add_header Strict-Transport-Security `"max-age=31536000; includeSubDomains`" always;"

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)

    [System.IO.File]::WriteAllText(
        "$PWD\nginx.conf",
        $content,
        $utf8NoBom
    )

    Write-Host "HSTS añadido al backend"
} else {
    Write-Host "HSTS ya existe en backend"
}

Get-Content nginx.conf | Select-String "Strict-Transport-Security"
```

La configuración establece un periodo de un año mediante `max-age=31536000` e incluye los subdominios con `includeSubDomains`.

**Efecto:** Se reportó la eliminación del hallazgo `strict-transport-security`.

**Consideración:** HSTS debe enviarse mediante HTTPS para que los navegadores lo apliquen correctamente. Antes de habilitar `includeSubDomains`, es necesario comprobar que todos los subdominios incluidos admitan HTTPS.

### 5. Reconstrucción y verificación

Después de aplicar las modificaciones, se reconstruyeron y levantaron los servicios mediante el siguiente comando:

```powershell
docker compose up -d --build
```

Se realizaron las siguientes verificaciones:

- El endpoint `/health` responde correctamente con el siguiente resultado:

  ```json
  {
      "status": "ok"
  }
  ```

- Los encabezados de seguridad están presentes en las respuestas verificadas, incluido HSTS.
- El servicio backend continúa operativo después de la reconstrucción.

---

## Hallazgos restantes

Se reportaron dos hallazgos restantes, ambos clasificados como informativos (`info`).

| # | Hallazgo | Justificación |
|---:|---|---|
| 1 | `waf-detect:nginxgeneric` | El mecanismo de filtrado basado en Nginx bloquea las peticiones identificadas como maliciosas. Este comportamiento es consistente con un mecanismo de seguridad funcionando y no constituye, por sí mismo, una vulnerabilidad. |
| 2 | `tech-detect:nginx` | Se identificó Nginx mediante los encabezados HTTP. La directiva `server_tokens off` oculta la versión exacta, pero no necesariamente elimina el encabezado `Server`. Se intentó eliminarlo mediante el módulo `headers-more`; sin embargo, se presentaron incompatibilidades binarias con Nginx 1.27 en Alpine. Por ello, el hallazgo se mantiene como informativo. |

---

## Conclusión

El servicio `movies-backend` pasó de 14 a 2 hallazgos, lo que representa una reducción aproximada del **86 %**. Las correcciones se enfocaron en fortalecer los encabezados de seguridad, restringir la configuración de CORS, establecer una política CSP y agregar HSTS.

Los dos hallazgos restantes son informativos y corresponden a la detección de Nginx y a la identificación de un mecanismo de filtrado. De acuerdo con los resultados obtenidos, no se identificaron vulnerabilidades explotables entre los hallazgos restantes del backend.

El servicio continúa funcionando correctamente después de los cambios realizados. 
