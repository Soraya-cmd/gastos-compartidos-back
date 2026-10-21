from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import database
from config import SECRET_KEY

ALGORITMO = "HS256"          
HORAS_VALIDEZ = 24            


def _a_bytes(password: str) -> bytes:

    return password.encode("utf-8")[:72]


def cifrar_password(password: str) -> str:
    """Convierte la contraseña en una versión mezclada que no se puede deshacer."""
    return bcrypt.hashpw(_a_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    """Comprueba si la contraseña escrita coincide con la guardada."""
    return bcrypt.checkpw(_a_bytes(password), password_hash.encode("utf-8"))


def crear_token(usuario_id: int) -> str:
    """Crea la 'pulsera': un código firmado con el id del usuario y su caducidad."""
    caduca = datetime.now(timezone.utc) + timedelta(hours=HORAS_VALIDEZ)
    datos = {"sub": str(usuario_id), "exp": caduca}
    return jwt.encode(datos, SECRET_KEY, algorithm=ALGORITMO)


esquema_bearer = HTTPBearer()


async def usuario_actual(
    credenciales: HTTPAuthorizationCredentials = Depends(esquema_bearer),
    conexion=Depends(database.get_conexion),
):
    """Descubre quién hace la petición a partir del token.
    Las rutas protegidas la usan con Depends(usuario_actual)."""
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token no válido o caducado",
    )
    try:
        datos = jwt.decode(credenciales.credentials, SECRET_KEY, algorithms=[ALGORITMO])
        usuario_id = int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise error

    async with conexion.cursor() as cursor:
        await cursor.execute(
            "SELECT id, nombre, email FROM usuarios WHERE id = %s", (usuario_id,)
        )
        usuario = await cursor.fetchone()
    if usuario is None:
        raise error
    return usuario