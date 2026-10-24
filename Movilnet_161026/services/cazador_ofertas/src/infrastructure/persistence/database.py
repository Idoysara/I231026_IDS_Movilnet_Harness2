"""
Configuración del Motor de Base de Datos y Sesiones para Cazador de Ofertas Movilnet.
Soporta SQLite 3 local (offline-first) y PostgreSQL 16 + PostGIS para despliegues de producción.
Arquitectura Hexagonal (SQLAlchemy 2.0 DeclarativeBase).
"""
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

# Directorio de datos predeterminado para SQLite local
DEFAULT_DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))
DEFAULT_DB_PATH = os.path.join(DEFAULT_DB_DIR, "cazador_local.db")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

class Base(DeclarativeBase):
    """Clase base declarativa pura de SQLAlchemy 2.0."""
    pass

def obtener_engine(db_url: str = DATABASE_URL):
    """Crea y retorna un engine configurado con soporte para SQLite o PostgreSQL."""
    connect_args = {}
    extra_kwargs = {}
    if db_url.startswith("sqlite"):
        os.makedirs(DEFAULT_DB_DIR, exist_ok=True)
        connect_args = {"check_same_thread": False}
        from sqlalchemy.pool import NullPool
        extra_kwargs["poolclass"] = NullPool
    
    return create_engine(
        db_url,
        connect_args=connect_args,
        echo=False,
        future=True,
        **extra_kwargs
    )

engine = obtener_engine()
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

def get_db_session() -> Generator[Session, None, None]:
    """Generador de contexto para inyección de dependencia de sesión de base de datos."""
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()

def init_db(target_engine=None) -> None:
    """Crea todas las tablas declaradas en el target_engine y asegura columnas espaciales."""
    from sqlalchemy import text
    from . import models  # noqa: F401 - Asegura registro de modelos en Base.metadata
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
    try:
        with eng.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(comercios);")).fetchall()
            cols = {row[1] for row in res}
            if cols and "tipo_cobertura" not in cols:
                conn.execute(text("ALTER TABLE comercios ADD COLUMN tipo_cobertura VARCHAR(30) DEFAULT 'PUNTO_INTERES';"))
            if cols and "zona_sector" not in cols:
                conn.execute(text("ALTER TABLE comercios ADD COLUMN zona_sector VARCHAR(80);"))
            if cols and "radio_cobertura_m" not in cols:
                conn.execute(text("ALTER TABLE comercios ADD COLUMN radio_cobertura_m FLOAT DEFAULT 500.0;"))
            if cols and "direccion" not in cols:
                conn.execute(text("ALTER TABLE comercios ADD COLUMN direccion VARCHAR(255);"))
            conn.commit()
    except Exception:
        pass

