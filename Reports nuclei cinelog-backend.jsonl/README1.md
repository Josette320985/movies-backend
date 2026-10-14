# movies-backend

## Preparación del servicio

```powershell
cd C:\Users\naher\Documents\PracticaFinal\movies-backend
docker compose up -d
```

## Verificación de red del contenedor

```powershell
docker inspect movies-backend --format '{{range $k, $v := .NetworkSettings.Networks}}{{println $k}}{{end}}'
```

Red detectada:

```text
ldap-keycloak-oauth2-lab_auth-network
```

## Ajuste de Fail2Ban para permitir el escaneo

```powershell
docker exec movies-backend fail2ban-client set http-flood maxretry 500
```

## Primer escaneo con Nuclei

```powershell
docker run --rm --network ldap-keycloak-oauth2-lab_auth-network -v "${PWD}\reports:/reports" -v "nuclei-templates-cache:/root/nuclei-templates" projectdiscovery/nuclei:latest -target http://movies-backend:80/health -severity info,low,medium -rate-limit 30 -timeout 10 -jsonl-export /reports/nuclei-cinelog-backend.jsonl
```

## Resultados del primer escaneo

- Servicio: **movies-backend**
- Hallazgos: **14**
- Problemas principales:
  - CORS wildcard
  - Headers de seguridad