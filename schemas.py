from pydantic import BaseModel, Field


class UsuarioRegistro(BaseModel):
    """Datos que envía una persona al registrarse."""
    nombre: str = Field(min_length=2, max_length=100)
    
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=150)
    password: str = Field(min_length=6, max_length=72)


class UsuarioLogin(BaseModel):
    """Datos que envía una persona al iniciar sesión."""
    email: str
    password: str


class UsuarioRespuesta(BaseModel):
    """Lo que devolvemos de un usuario. Nunca incluye la contraseña."""
    id: int
    nombre: str
    email: str


class Token(BaseModel):
    """La 'pulsera' que recibe el usuario al iniciar sesión."""
    access_token: str
    token_type: str