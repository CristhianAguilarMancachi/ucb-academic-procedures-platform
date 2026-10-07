"""Preflight de M03 sin ejecutar SQL, abrir conexiones ni iniciar FastAPI.

Desde backend: PYTHONDONTWRITEBYTECODE=1 python scripts/verificar_m03.py
"""
from importlib import import_module, util
from pathlib import Path
import re
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def elementos_sql(texto):
    """Separa columnas/constraints a nivel superior (no es un ejecutor SQL)."""
    resultado = []
    inicio = profundidad = 0
    comilla = None
    for pos, char in enumerate(texto):
        if comilla:
            if char == comilla:
                comilla = None
        elif char in "'\"":
            comilla = char
        elif char == '(':
            profundidad += 1
        elif char == ')':
            profundidad -= 1
        elif char == ',' and profundidad == 0:
            resultado.append(texto[inicio:pos].strip())
            inicio = pos + 1
    resultado.append(texto[inicio:].strip())
    return resultado


def tablas_sql(texto):
    tablas = {}
    texto = re.sub(r'--[^\n]*', '', texto)
    for match in re.finditer(r'CREATE TABLE (\w+)\s*\(', texto):
        nombre = match[1]
        assert nombre not in tablas, f'Tabla duplicada: {nombre}'
        inicio = match.end()
        profundidad = 1
        comilla = None
        for pos in range(inicio, len(texto)):
            char = texto[pos]
            if comilla:
                if char == comilla:
                    comilla = None
            elif char in "'\"":
                comilla = char
            elif char == '(':
                profundidad += 1
            elif char == ')':
                profundidad -= 1
            if profundidad == 0:
                tablas[nombre] = elementos_sql(texto[inicio:pos])
                break
        else:
            raise AssertionError(f'Tabla incompleta: {nombre}')
    return tablas


def main():
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    from sqlalchemy.schema import CreateTable, CreateIndex
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import configure_mappers

    @event.listens_for(Engine, 'do_connect')
    def prohibir_conexion(*args):
        raise AssertionError('Este preflight no puede conectar a PostgreSQL.')

    archivos = list((BACKEND / 'app').rglob('*.py')) + list((BACKEND / 'mock_pago_api').rglob('*.py'))
    for archivo in archivos:
        compile(archivo.read_bytes(), str(archivo), 'exec')
    print(f'Compilación en memoria: {len(archivos)} archivos Python OK')

    import app.models
    import app.models.gestion_seguimiento as modelos
    from app.db.base import Base
    configure_mappers()
    print('configure_mappers: OK')

    maestro = (BACKEND / 'database.sql').read_text()
    manual = (BACKEND / 'sql/manual/gestion_seguimiento_fases_4_5_6.sql').read_text()
    tablas = tablas_sql(maestro)
    nuevas = tablas_sql(manual)
    assert set(nuevas) == {'solicitud_etapa', 'solicitud_historial', 'solicitud_observacion', 'solicitud_resultado', 'solicitud_entrega'}
    assert len(tablas) == 27
    assert not re.search(r'\b(?:DROP TABLE|DELETE FROM|TRUNCATE|UPDATE|INSERT INTO)\b', re.sub(r'--[^\n]*','',manual).replace('BEFORE UPDATE', 'BEFORE_CHANGE'))
    assert not re.search(r'INSERT INTO usuario\b', maestro)
    for nombre in modelos.__all__:
        tabla = getattr(modelos, nombre).__table__
        columnas = {x.split()[0] for x in tablas[tabla.name] if not x.startswith(('CONSTRAINT ', 'FOREIGN KEY ', 'UNIQUE ', 'CHECK '))}
        assert columnas == set(tabla.columns.keys()), f'Columnas SQL/ORM distintas en {tabla.name}: {columnas ^ set(tabla.columns.keys())}'
        str(CreateTable(tabla).compile(dialect=postgresql.dialect()))
        for indice in tabla.indexes:
            str(CreateIndex(indice).compile(dialect=postgresql.dialect()))
        for constraint in tabla.constraints:
            if constraint.name:
                assert constraint.name in maestro, f'Constraint ausente: {constraint.name}'
    for nombre, elementos in nuevas.items():
        normalizar = lambda xs: sorted(re.sub(r'\s+', ' ', x).strip() for x in xs)
        assert normalizar(elementos) == normalizar(tablas[nombre]), f'Tabla nueva diferente entre SQL manual/maestro: {nombre}'
    # Verifica las relaciones compuestas añadidas, no solo nombres de columnas.
    compactar = lambda texto: re.sub(r'\s+', '', texto).lower()
    for nombre in modelos.__all__:
        tabla = getattr(modelos, nombre).__table__
        cuerpo = compactar(' '.join(tablas[tabla.name]))
        for fk in tabla.foreign_key_constraints:
            if len(fk.elements) > 1:
                cols = ','.join(e.parent.name for e in fk.elements)
                destino = fk.elements[0].column.table.name
                refs = ','.join(e.column.name for e in fk.elements)
                firma = f'foreignkey({cols})references{destino}({refs})'
                assert firma in compactar(maestro), f'FK compuesta SQL/ORM distinta: {fk.name}'
        for columna in tabla.columns:
            if columna.name in ('id_solicitud_etapa', 'id_solicitud_requisito') and tabla.name == 'solicitud_historial':
                assert columna.nullable and str(columna.type) == 'BIGINT'
    for nombre in ('uq_solicitud_etapa_inicial', 'uq_solicitud_etapa_final', 'uq_solicitud_etapa_en_curso'):
        indice = next(i for i in modelos.SolicitudEtapa.__table__.indexes if i.name == nombre)
        assert indice.unique
        assert compactar(str(CreateIndex(indice).compile(dialect=postgresql.dialect()))) in compactar(manual)
    assert "estado<>'en_proceso'orid_etapa_actualisnotnull" in compactar(manual)
    print('SQL estático: 27 tablas maestras; 18 modelos M03 y 5 tablas nuevas coherentes. DDL compilado sin ejecutar.')

    from fastapi import FastAPI
    app = FastAPI()
    rutas = ['solicitudes', 'admin_solicitudes', 'tramites', 'perfil_academico', 'seguimiento']
    if util.find_spec('python_multipart'):
        rutas += ['admin_tramites', 'admin_unidades']
    else:
        print('LIMITACIÓN: faltó python-multipart; se omiten routers de configuración que importan auth.')
    for nombre in rutas:
        app.include_router(import_module('app.api.routes.gestion_seguimiento.' + nombre).router, prefix='/api')
    esquema = app.openapi()
    operaciones = [operacion['operationId'] for path in esquema['paths'].values() for metodo, operacion in path.items() if metodo in ('get', 'post', 'put', 'patch', 'delete')]
    assert len(operaciones) == len(set(operaciones)), 'operationId duplicado'
    assert '/api/admin/solicitudes/{id_solicitud}/entregar' in esquema['paths']
    assert '/api/solicitudes/{id_solicitud}/seguimiento' in esquema['paths']
    from app.schemas.gestion_seguimiento.tramite import TramiteDetalleResponse
    from app.schemas.gestion_seguimiento.solicitud_administrativa import SolicitudAdministrativaDetalleResponse
    for schema in (TramiteDetalleResponse, SolicitudAdministrativaDetalleResponse):
        schema.model_json_schema()
    print(f'OpenAPI: {len(esquema["paths"])} rutas y {len(operaciones)} operaciones OK; schemas de configuración OK')
    print('NO se ejecutó SQL ni se inició el servidor o el módulo RAG.')


if __name__ == '__main__':
    main()
