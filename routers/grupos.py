from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, status

import database
from schemas import GrupoDetalle, GrupoNuevo, GrupoResumen
from security import usuario_actual


router = APIRouter(prefix="/grupos", tags=["Grupos"])


def redondear(valor: Decimal) -> Decimal:
    """Redondea a céntimos (2 decimales)."""
    return valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def construir_detalle(conexion, grupo_id: int, usuario_id: int) -> dict:
    """Reúne todos los datos de un grupo y calcula lo que debe cada persona.
    Si la persona no es miembro, responde 'no encontrado'."""
    async with conexion.cursor() as cursor:
        
        await cursor.execute(
            """SELECT g.id, g.titulo, g.descripcion, g.creador_id
               FROM grupos g
               JOIN miembros_grupo m ON m.grupo_id = g.id
               WHERE g.id = %s AND m.usuario_id = %s""",
            (grupo_id, usuario_id),
        )
        grupo = await cursor.fetchone()
        if grupo is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")

        await cursor.execute(
            "SELECT id, concepto, categoria, importe FROM gastos WHERE grupo_id = %s ORDER BY id",
            (grupo_id,),
        )
        gastos = await cursor.fetchall()

        await cursor.execute(
            """SELECT u.id AS usuario_id, u.nombre, u.email, m.porcentaje
               FROM miembros_grupo m
               JOIN usuarios u ON u.id = m.usuario_id
               WHERE m.grupo_id = %s
               ORDER BY m.id""",
            (grupo_id,),
        )
        miembros = await cursor.fetchall()

        await cursor.execute(
            """SELECT p.id, p.usuario_id, u.nombre, p.importe, p.fecha, p.nota
               FROM pagos p
               JOIN usuarios u ON u.id = p.usuario_id
               WHERE p.grupo_id = %s
               ORDER BY p.fecha DESC, p.id DESC""",
            (grupo_id,),
        )
        pagos = await cursor.fetchall()

    
    total = sum((g["importe"] for g in gastos), Decimal("0"))

    
    pagado_por = {}
    for p in pagos:
        anterior = pagado_por.get(p["usuario_id"], Decimal("0"))
        pagado_por[p["usuario_id"]] = anterior + p["importe"]

    lista_miembros = []
    porcentaje_asignado = Decimal("0")
    for m in miembros:
        porcentaje_asignado += m["porcentaje"]
        debe = redondear(total * m["porcentaje"] / 100)
        pagado = pagado_por.get(m["usuario_id"], Decimal("0"))
        lista_miembros.append({
            "usuario_id": m["usuario_id"],
            "nombre": m["nombre"],
            "email": m["email"],
            "es_creador": m["usuario_id"] == grupo["creador_id"],
            "porcentaje": float(m["porcentaje"]),
            "debe": float(debe),
            "pagado": float(pagado),
            "pendiente": float(debe - pagado),
        })

    total_pagado = sum(pagado_por.values(), Decimal("0"))

    return {
        "id": grupo["id"],
        "titulo": grupo["titulo"],
        "descripcion": grupo["descripcion"] or "",
        "creador_id": grupo["creador_id"],
        "soy_creador": grupo["creador_id"] == usuario_id,
        "total": float(total),
        "porcentaje_asignado": float(porcentaje_asignado),
        "reparto_completo": porcentaje_asignado == 100,
        "total_pagado": float(total_pagado),
        "total_pendiente": float(total - total_pagado),
        "gastos": [
            {"id": g["id"], "concepto": g["concepto"],
             "categoria": g["categoria"], "importe": float(g["importe"])}
            for g in gastos
        ],
        "miembros": lista_miembros,
        "pagos": [
            {"id": p["id"], "usuario_id": p["usuario_id"], "nombre": p["nombre"],
             "importe": float(p["importe"]), "fecha": p["fecha"], "nota": p["nota"]}
            for p in pagos
        ],
    }


@router.post("", response_model=GrupoDetalle, status_code=status.HTTP_201_CREATED)
async def crear_grupo(
    datos: GrupoNuevo,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Crea el grupo con sus gastos. Quien lo crea queda como creador y miembro (0 %)."""
    
    await conexion.begin()
    try:
        async with conexion.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO grupos (titulo, descripcion, creador_id) VALUES (%s, %s, %s)",
                (datos.titulo.strip(), datos.descripcion.strip(), usuario["id"]),
            )
            grupo_id = cursor.lastrowid

            
            await cursor.execute(
                "INSERT INTO miembros_grupo (grupo_id, usuario_id, porcentaje) VALUES (%s, %s, 0)",
                (grupo_id, usuario["id"]),
            )

            await cursor.executemany(
                "INSERT INTO gastos (grupo_id, concepto, categoria, importe) VALUES (%s, %s, %s, %s)",
                [(grupo_id, g.concepto.strip(), g.categoria, g.importe) for g in datos.gastos],
            )
        await conexion.commit()
    except Exception:
        await conexion.rollback()   
        raise

    return await construir_detalle(conexion, grupo_id, usuario["id"])


@router.get("", response_model=list[GrupoResumen])
async def mis_grupos(
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Lista los grupos de los que formo parte, como creador o como invitado."""
    async with conexion.cursor() as cursor:
        await cursor.execute(
            """SELECT g.id, g.titulo, g.descripcion, g.creador_id,
                      COALESCE(SUM(ga.importe), 0) AS total
               FROM grupos g
               JOIN miembros_grupo m ON m.grupo_id = g.id AND m.usuario_id = %s
               LEFT JOIN gastos ga ON ga.grupo_id = g.id
               GROUP BY g.id, g.titulo, g.descripcion, g.creador_id, g.creado_en
               ORDER BY g.creado_en DESC""",
            (usuario["id"],),
        )
        filas = await cursor.fetchall()

    return [
        {
            "id": f["id"],
            "titulo": f["titulo"],
            "descripcion": f["descripcion"] or "",
            "total": float(f["total"]),
            "rol": "creador" if f["creador_id"] == usuario["id"] else "invitado",
        }
        for f in filas
    ]


@router.get("/{grupo_id}", response_model=GrupoDetalle)
async def detalle_grupo(
    grupo_id: int,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Detalle del grupo con gastos, miembros, pagos y deudas. Lo ve cualquier miembro."""
    return await construir_detalle(conexion, grupo_id, usuario["id"])