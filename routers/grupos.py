from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, status

import database
from schemas import (
    GastoNuevo, GrupoDetalle, GrupoNuevo, GrupoResumen,
    MiembroNuevo, PagoNuevo, PorcentajeCambio,
    MensajeNuevo, MensajeRespuesta, MiembroNuevo, PagoNuevo, PorcentajeCambio,
)
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





async def exigir_creador(conexion, grupo_id: int, usuario_id: int):
    """Comprueba que la persona es el creador del grupo.
    - Si no es miembro: 404 (ni siquiera sabe que el grupo existe).
    - Si es miembro pero no creador: 403 (solo puede mirar)."""
    async with conexion.cursor() as cursor:
        await cursor.execute(
            """SELECT g.creador_id
               FROM grupos g
               JOIN miembros_grupo m ON m.grupo_id = g.id
               WHERE g.id = %s AND m.usuario_id = %s""",
            (grupo_id, usuario_id),
        )
        fila = await cursor.fetchone()
    if fila is None:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if fila["creador_id"] != usuario_id:
        raise HTTPException(status_code=403, detail="Solo el creador del grupo puede hacer esto")


async def comprobar_porcentaje(cursor, grupo_id: int, nuevo: Decimal, excluir_usuario_id=None):
    """Evita que los porcentajes del grupo sumen más de 100."""
    sql = "SELECT COALESCE(SUM(porcentaje), 0) AS suma FROM miembros_grupo WHERE grupo_id = %s"
    parametros = [grupo_id]
    if excluir_usuario_id is not None:
    
        sql += " AND usuario_id <> %s"
        parametros.append(excluir_usuario_id)
    await cursor.execute(sql, parametros)
    suma = (await cursor.fetchone())["suma"]
    if suma + nuevo > 100:
        libre = Decimal("100") - suma
        raise HTTPException(
            status_code=422,
            detail=f"Los porcentajes no pueden superar el 100 %. Quedan {libre} % por asignar",
        )


@router.post("/{grupo_id}/miembros", response_model=GrupoDetalle, status_code=status.HTTP_201_CREATED)
async def invitar_miembro(
    grupo_id: int,
    datos: MiembroNuevo,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Invita a una persona ya registrada, con su porcentaje."""
    await exigir_creador(conexion, grupo_id, usuario["id"])
    email = datos.email.strip().lower()

    async with conexion.cursor() as cursor:
        await cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        invitado = await cursor.fetchone()
        if invitado is None:
            raise HTTPException(
                status_code=404,
                detail="No existe ningún usuario con ese email. Debe registrarse primero",
            )

        await cursor.execute(
            "SELECT id FROM miembros_grupo WHERE grupo_id = %s AND usuario_id = %s",
            (grupo_id, invitado["id"]),
        )
        if await cursor.fetchone():
            raise HTTPException(status_code=409, detail="Esa persona ya está en el grupo")

        await comprobar_porcentaje(cursor, grupo_id, datos.porcentaje)

        await cursor.execute(
            "INSERT INTO miembros_grupo (grupo_id, usuario_id, porcentaje) VALUES (%s, %s, %s)",
            (grupo_id, invitado["id"], datos.porcentaje),
        )

    return await construir_detalle(conexion, grupo_id, usuario["id"])


@router.put("/{grupo_id}/miembros/{usuario_id}", response_model=GrupoDetalle)
async def cambiar_porcentaje(
    grupo_id: int,
    usuario_id: int,
    datos: PorcentajeCambio,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Cambia el porcentaje de un miembro (también el del propio creador)."""
    await exigir_creador(conexion, grupo_id, usuario["id"])

    async with conexion.cursor() as cursor:
        await cursor.execute(
            "SELECT id FROM miembros_grupo WHERE grupo_id = %s AND usuario_id = %s",
            (grupo_id, usuario_id),
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Esa persona no pertenece al grupo")

        await comprobar_porcentaje(cursor, grupo_id, datos.porcentaje, excluir_usuario_id=usuario_id)

        await cursor.execute(
            "UPDATE miembros_grupo SET porcentaje = %s WHERE grupo_id = %s AND usuario_id = %s",
            (datos.porcentaje, grupo_id, usuario_id),
        )

    return await construir_detalle(conexion, grupo_id, usuario["id"])


@router.post("/{grupo_id}/gastos", response_model=GrupoDetalle, status_code=status.HTTP_201_CREATED)
async def anadir_gasto(
    grupo_id: int,
    datos: GastoNuevo,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Añade un gasto más al desglose del grupo."""
    await exigir_creador(conexion, grupo_id, usuario["id"])

    async with conexion.cursor() as cursor:
        await cursor.execute(
            "INSERT INTO gastos (grupo_id, concepto, categoria, importe) VALUES (%s, %s, %s, %s)",
            (grupo_id, datos.concepto.strip(), datos.categoria, datos.importe),
        )

    return await construir_detalle(conexion, grupo_id, usuario["id"])


@router.delete("/{grupo_id}/gastos/{gasto_id}", response_model=GrupoDetalle)
async def borrar_gasto(
    grupo_id: int,
    gasto_id: int,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Borra un gasto (por ejemplo, si se anotó por error)."""
    await exigir_creador(conexion, grupo_id, usuario["id"])

    async with conexion.cursor() as cursor:
        await cursor.execute(
            "DELETE FROM gastos WHERE id = %s AND grupo_id = %s", (gasto_id, grupo_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")

    return await construir_detalle(conexion, grupo_id, usuario["id"])


@router.post("/{grupo_id}/pagos", response_model=GrupoDetalle, status_code=status.HTTP_201_CREATED)
async def anotar_pago(
    grupo_id: int,
    datos: PagoNuevo,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Anota un pago que ya se ha hecho fuera de la app. La deuda se recalcula sola."""
    await exigir_creador(conexion, grupo_id, usuario["id"])

    async with conexion.cursor() as cursor:
        await cursor.execute(
            "SELECT id FROM miembros_grupo WHERE grupo_id = %s AND usuario_id = %s",
            (grupo_id, datos.usuario_id),
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=422, detail="Esa persona no pertenece al grupo")

        await cursor.execute(
            "INSERT INTO pagos (grupo_id, usuario_id, importe, fecha, nota) VALUES (%s, %s, %s, %s, %s)",
            (grupo_id, datos.usuario_id, datos.importe,
             datos.fecha or date.today(), datos.nota.strip() or None),
        )

    return await construir_detalle(conexion, grupo_id, usuario["id"])


@router.delete("/{grupo_id}/pagos/{pago_id}", response_model=GrupoDetalle)
async def borrar_pago(
    grupo_id: int,
    pago_id: int,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Borra un pago anotado por error."""
    await exigir_creador(conexion, grupo_id, usuario["id"])

    async with conexion.cursor() as cursor:
        await cursor.execute(
            "DELETE FROM pagos WHERE id = %s AND grupo_id = %s", (pago_id, grupo_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

    return await construir_detalle(conexion, grupo_id, usuario["id"])





@router.delete("/{grupo_id}/miembros/{usuario_id}", response_model=GrupoDetalle)
async def quitar_miembro(
    grupo_id: int,
    usuario_id: int,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Quita a una persona del grupo (solo el creador, y nunca al propio creador)."""
    await exigir_creador(conexion, grupo_id, usuario["id"])

    

    if usuario_id == usuario["id"]:
        raise HTTPException(status_code=422, detail="El creador no puede salir del grupo")

    async with conexion.cursor() as cursor:
       
        await cursor.execute(
            "SELECT COUNT(*) AS total FROM pagos WHERE grupo_id = %s AND usuario_id = %s",
            (grupo_id, usuario_id),
        )
        if (await cursor.fetchone())["total"] > 0:
            raise HTTPException(
                status_code=409,
                detail="Esa persona tiene pagos anotados. Bórralos primero",
            )

        await cursor.execute(
            "DELETE FROM miembros_grupo WHERE grupo_id = %s AND usuario_id = %s",
            (grupo_id, usuario_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Esa persona no pertenece al grupo")

    return await construir_detalle(conexion, grupo_id, usuario["id"])




@router.post("/{grupo_id}/repartir-igual", response_model=GrupoDetalle)
async def repartir_igual(
    grupo_id: int,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Reparte el 100 % a partes iguales entre todos los miembros (solo el creador).
    Los céntimos que sobran al dividir se los queda el creador, para sumar justo 100."""
    await exigir_creador(conexion, grupo_id, usuario["id"])

    await conexion.begin()
    try:
        async with conexion.cursor() as cursor:
            await cursor.execute(
                "SELECT usuario_id FROM miembros_grupo WHERE grupo_id = %s", (grupo_id,)
            )
            miembros = await cursor.fetchall()
            cantidad = len(miembros)

           
            base = (Decimal("100") / cantidad).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
            sobrante = Decimal("100") - base * cantidad   # ej.: 0,01

            for m in miembros:
                porcentaje = base + (sobrante if m["usuario_id"] == usuario["id"] else 0)
                await cursor.execute(
                    "UPDATE miembros_grupo SET porcentaje = %s WHERE grupo_id = %s AND usuario_id = %s",
                    (porcentaje, grupo_id, m["usuario_id"]),
                )
        await conexion.commit()
    except Exception:
        await conexion.rollback()
        raise

    return await construir_detalle(conexion, grupo_id, usuario["id"])








async def exigir_miembro(conexion, grupo_id: int, usuario_id: int):
    """Comprueba que la persona pertenece al grupo. Si no, 404."""
    async with conexion.cursor() as cursor:
        await cursor.execute(
            "SELECT id FROM miembros_grupo WHERE grupo_id = %s AND usuario_id = %s",
            (grupo_id, usuario_id),
        )
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")


@router.get("/{grupo_id}/mensajes", response_model=list[MensajeRespuesta])
async def listar_mensajes(
    grupo_id: int,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Devuelve los últimos 200 mensajes del grupo, del más antiguo al más nuevo."""
    await exigir_miembro(conexion, grupo_id, usuario["id"])

    async with conexion.cursor() as cursor:
        await cursor.execute(
            """SELECT m.id, m.usuario_id, u.nombre, m.contenido, m.creado_en
               FROM mensajes m
               JOIN usuarios u ON u.id = m.usuario_id
               WHERE m.grupo_id = %s
               ORDER BY m.id DESC
               LIMIT 200""",
            (grupo_id,),
        )
        filas = await cursor.fetchall()

    
    return list(reversed(filas))


@router.post("/{grupo_id}/mensajes", response_model=MensajeRespuesta, status_code=status.HTTP_201_CREATED)
async def enviar_mensaje(
    grupo_id: int,
    datos: MensajeNuevo,
    usuario=Depends(usuario_actual),
    conexion=Depends(database.get_conexion),
):
    """Un miembro del grupo (creador o invitado) escribe un mensaje."""
    await exigir_miembro(conexion, grupo_id, usuario["id"])

    contenido = datos.contenido.strip()
    if not contenido:
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío")

    async with conexion.cursor() as cursor:
        await cursor.execute(
            "INSERT INTO mensajes (grupo_id, usuario_id, contenido) VALUES (%s, %s, %s)",
            (grupo_id, usuario["id"], contenido),
        )
        nuevo_id = cursor.lastrowid

        await cursor.execute(
            """SELECT m.id, m.usuario_id, u.nombre, m.contenido, m.creado_en
               FROM mensajes m
               JOIN usuarios u ON u.id = m.usuario_id
               WHERE m.id = %s""",
            (nuevo_id,),
        )
        return await cursor.fetchone()