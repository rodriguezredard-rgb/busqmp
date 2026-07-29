from sqlalchemy import Column, Integer, String, Date, Float, Text, UniqueConstraint
from app.models.database import Base


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_opportunity_source_external_id"),)

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)  # mercado_publico / compras_agiles
    opportunity_type = Column(String(50), nullable=False)  # licitacion / compra_agil
    external_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    organization = Column(String(500), nullable=True)
    category = Column(String(200), nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(20), nullable=True)
    publish_date = Column(Date, nullable=True)
    award_date = Column(Date, nullable=True)
    closing_date = Column(Date, nullable=True)
    status = Column(String(100), nullable=True)
    region = Column(String(200), nullable=True)
    tags = Column(String(500), nullable=True)
    url = Column(String(1000), nullable=True)
    notes = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
