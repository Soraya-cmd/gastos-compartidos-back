from fastapi import APIRouter, Depends, HTTPException, status

import database
from schemas import Token, UsuarioLogin, UsuarioRegistro, UsuarioRespuesta
from security import cifrar_password, crear_token, usuario_actual, verificar_password


router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
async def registro(datos: UsuarioRegistro, conexion=Depends(database.get_conexion)):
    nombre = datos.nombre.strip()
    email = datos.email.strip().lower()   
    
    async with conexion.cursor() as cursor:
    
        await cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        if await cursor.fetchone():
            raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email")

        
       
        await cursor.execute(
            "INSERT INTO usuarios (nombre, email, password_hash) VALUES (%s, %s, %s)",
            (nombre, email, cifrar_password(datos.password)),
        )
        nuevo_id = cursor.lastrowid   # el id que MySQL acaba de asignar

    return {"id": nuevo_id, "nombre": nombre, "email": email}


@router.post("/login", response_model=Token)
async def login(datos: UsuarioLogin, conexion=Depends(database.get_conexion)):
    email = datos.email.strip().lower()

    async with conexion.cursor() as cursor:
        await cursor.execute(
            "SELECT id, password_hash FROM usuarios WHERE email = %s", (email,)
        )
        usuario = await cursor.fetchone()

    
    if usuario is None or not verificar_password(datos.password, usuario["password_hash"]):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    return {"access_token": crear_token(usuario["id"]), "token_type": "bearer"}


@router.get("/yo", response_model=UsuarioRespuesta)
async def yo(usuario=Depends(usuario_actual)):
    """Ruta protegida: devuelve el usuario que ha iniciado sesión."""
    return usuario