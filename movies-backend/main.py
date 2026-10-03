import os
import httpx
from typing import Annotated, List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt, JWTError
from pydantic import BaseModel

# ============ CONFIGURACIÓN ============
# URL publica: la que va en el "iss" del JWT (lo que el usuario ve en el navegador)
KC_PUBLIC = "http://localhost:8081"

# URL interna: la que el backend usa para hablar con Keycloak via Docker
KC_INTERNAL = "http://keycloak-proxy:80"

REALM = "cybersecurity"
CLIENT_ID = "fastapi-api"

# El "issuer" debe coincidir con el valor "iss" del JWT (URL publica)
ISSUER = f"{KC_PUBLIC}/realms/{REALM}"

# El JWKS se obtiene via la red interna de Docker
JWKS_URL = f"{KC_INTERNAL}/realms/{REALM}/protocol/openid-connect/certs"

# ============ APP ============
app = FastAPI(title="Movies API")

# CORS: permite que Vue llame a este backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{ISSUER}/protocol/openid-connect/auth",
    tokenUrl=f"{ISSUER}/protocol/openid-connect/token",
    scopes={"openid": "OpenID Connect identity"},
)

# ============ MODELOS ============
class Movie(BaseModel):
    id: int
    title: str
    year: int
    genre: str

class MovieCreate(BaseModel):
    title: str
    year: int
    genre: str

# Base de datos en memoria
movies_db: List[Movie] = [
    Movie(id=1, title="Inception", year=2010, genre="Sci-Fi"),
    Movie(id=2, title="The Matrix", year=1999, genre="Sci-Fi"),
    Movie(id=3, title="Interstellar", year=2014, genre="Sci-Fi"),
]

# ============ VALIDACIÓN DE JWT ============
async def current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(JWKS_URL, timeout=5)
            r.raise_for_status()
            jwks = r.json()

        header = jwt.get_unverified_header(token)
        key = next((k for k in jwks["keys"] if k.get("kid") == header.get("kid")), None)
        if not key:
            raise HTTPException(401, "Signing key not found")

        payload = jwt.decode(
            token, key, algorithms=["RS256"],
            audience=CLIENT_ID, issuer=ISSUER
        )
        print(f"JWT válido para: {payload.get('preferred_username')}")
        return payload
    except (JWTError, httpx.HTTPError) as e:
        print(f"JWT inválido: {e}")
        raise HTTPException(401, f"Invalid access token: {e}",
                            headers={"WWW-Authenticate": "Bearer"})

# ============ ENDPOINTS ============
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/movies", response_model=List[Movie])
async def get_movies(user: Annotated[dict, Depends(current_user)]):
    print(f"GET /api/movies solicitado por: {user.get('preferred_username')}")
    return movies_db

@app.post("/api/movies", response_model=Movie)
async def add_movie(movie: MovieCreate, user: Annotated[dict, Depends(current_user)]):
    new_id = max([m.id for m in movies_db], default=0) + 1
    new_movie = Movie(id=new_id, **movie.dict())
    movies_db.append(new_movie)
    print(f"POST /api/movies - {user.get('preferred_username')} agregó: {new_movie.title}")
    return new_movie

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)