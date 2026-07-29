from sqlalchemy import Column, Date, DateTime, Integer, JSON, Numeric, String, Text
from app.models.database import Base


class Licitacion(Base):
    """Tabla existente administrada por Peken. Este proyecto solo la consulta."""
    __tablename__ = "licitaciones"
    __table_args__ = {"extend_existing": True}

    id = Column(Text, primary_key=True)
    nombre = Column(Text, nullable=False)
    descripcion = Column(Text, nullable=False)
    organismo = Column(Text, nullable=False)
    moneda = Column(Text, nullable=False)
    monto_licitacion = Column(Text, nullable=False)
    fecha_adjudicacion = Column(Date, nullable=False)
    search_text = Column(Text, nullable=False)
    source_detail = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class CompraAgil(Base):
    """Copia local sincronizada desde la API oficial de Compra Ágil V2."""
    __tablename__ = "compras_agiles"

    codigo = Column(String(100), primary_key=True)
    nombre = Column(Text, nullable=False, default="")
    descripcion = Column(Text, nullable=False, default="")
    estado = Column(String(80), nullable=False, default="")
    organismo = Column(Text, nullable=False, default="")
    rut_organismo = Column(String(30), nullable=False, default="")
    unidad_compra = Column(Text, nullable=False, default="")
    region_codigo = Column(Integer, nullable=True)
    region = Column(String(150), nullable=False, default="")
    moneda = Column(String(20), nullable=False, default="CLP")
    monto = Column(Numeric, nullable=True)
    fecha_publicacion = Column(DateTime(timezone=True), nullable=True)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)
    fecha_ultimo_cambio = Column(DateTime(timezone=True), nullable=True, index=True)
    search_text = Column(Text, nullable=False, default="", index=True)
    source_detail = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), nullable=False)
