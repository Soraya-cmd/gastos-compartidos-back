# Compartir gastos · Backend (API REST)

API del proyecto final del **Máster en Programación y Desarrollo Web Full Stack**.
La aplicación permite dividir los gastos de una boda o despedida entre varias personas:
cada usuario se registra, crea grupos, invita a otros con un porcentaje y se calcula
automáticamente lo que debe y lo que ha pagado cada integrante.

- Frontend (Angular): https://github.com/Soraya-cmd/gastos-compartidos-front
- Autora: Soraya Arbona Martínez

## Tecnologías

| Parte | Tecnología |
|---|---|
| Lenguaje | Python 3.13 |
| Framework | FastAPI + uvicorn |
| Base de datos | MySQL 8 (acceso asíncrono con `aiomysql`) |
| Seguridad | `bcrypt` (contraseñas) y `PyJWT` (token de sesión de 24 h) |
| Configuración | `python-dotenv` (archivo `.env`) |

## Estructura del proyecto

```
back/
├── main.py              # Arranque de la app, CORS y routers
├── config.py            # Lee las variables del archivo .env
├── database.py          # Conexión (pool) a MySQL
├── security.py          # Cifrado de contraseñas y token JWT
├── schemas.py           # Modelos de datos (validación de entradas y salidas)
├── routers/
│   ├── auth.py          # Registro, login y usuario actual
│   └── grupos.py        # Grupos, gastos, miembros, pagos y mensajes
├── database/
│   └── esquema.sql      # Script que crea la base de datos y las 6 tablas
├── requirements.txt     # Dependencias de Python
├── .env.example         # Plantilla de variables de entorno
└── .gitignore
```

## Requisitos previos

- Python 3.13
- MySQL 8 (y, opcionalmente, MySQL Workbench)
- Git

## Instalación (Windows)

### 1. Clonar el repositorio

```
git clone https://github.com/Soraya-cmd/gastos-compartidos-back.git
cd gastos-compartidos-back
```

### 2. Crear la base de datos

Abre MySQL Workbench y ejecuta el contenido de `database/esquema.sql`.
Crea la base `gastos_compartidos` y sus tablas.

Después crea un usuario propio con permisos solo sobre esa base
(sustituye `TU_CONTRASEÑA` por una contraseña nueva que elijas tú):

```sql
CREATE USER 'gastos_user'@'localhost' IDENTIFIED BY 'TU_CONTRASEÑA';
GRANT ALL PRIVILEGES ON gastos_compartidos.* TO 'gastos_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Variables de entorno

Copia `.env.example` con el nombre `.env` y rellena tus valores:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=gastos_user
DB_PASSWORD=TU_CONTRASEÑA
DB_NAME=gastos_compartidos
SECRET_KEY=una_clave_larga_y_aleatoria
```

> El archivo `.env` contiene claves y **nunca se sube a Git** (está en `.gitignore`).
> Opcionalmente puede definirse `CORS_ORIGINS` (orígenes permitidos separados por comas;
> por defecto `http://localhost:4200,http://127.0.0.1:4200`).

### 4. Entorno virtual y dependencias

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 5. Arrancar la API

```
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000
- Documentación interactiva (Swagger): http://127.0.0.1:8000/docs

## Endpoints principales

Todas las rutas de `/grupos` requieren el token en la cabecera
`Authorization: Bearer <token>`.

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/registro` | Crear usuario |
| POST | `/auth/login` | Iniciar sesión (devuelve el token) |
| GET | `/auth/yo` | Datos del usuario actual |
| GET | `/grupos/` | Mis grupos |
| POST | `/grupos/` | Crear grupo con sus gastos |
| GET | `/grupos/{id}` | Detalle del grupo con deudas calculadas |
| POST | `/grupos/{id}/miembros` | Invitar a un usuario con un porcentaje (creador) |
| PUT | `/grupos/{id}/miembros/{usuario_id}` | Cambiar porcentaje (creador) |
| DELETE | `/grupos/{id}/miembros/{usuario_id}` | Quitar miembro sin pagos (creador) |
| POST | `/grupos/{id}/repartir-igual` | Repartir a partes iguales (creador) |
| POST / DELETE | `/grupos/{id}/gastos` · `/gastos/{gasto_id}` | Añadir o borrar gastos (creador) |
| POST / DELETE | `/grupos/{id}/pagos` · `/pagos/{pago_id}` | Registrar o borrar pagos (creador) |
| GET / POST | `/grupos/{id}/mensajes` | Leer y enviar mensajes del chat (miembros) |

## Reglas de negocio

- Solo el **creador** modifica gastos, porcentajes y pagos; los invitados solo consultan.
- Lo que debe cada persona: `debe = total × porcentaje / 100`.
- Lo que le queda: `pendiente = debe − pagado`.
- La suma de porcentajes no puede superar el 100 %.
- No se puede quitar a un miembro que ya tiene pagos ni al creador.
- Los pagos reales se hacen fuera de la aplicación: aquí solo se registran.

## Modelo de datos

Seis tablas: `usuarios`, `grupos`, `gastos`, `miembros_grupo`, `pagos` y `mensajes`.
Importes en `DECIMAL(10,2)` y borrado en cascada mediante claves foráneas.

## Ramas (GitFlow)

`main` (estable, etiqueta `v1.0`), `develop` (integración) y `feature/*` (una por funcionalidad).
