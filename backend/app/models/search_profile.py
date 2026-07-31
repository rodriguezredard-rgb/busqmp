from sqlalchemy import Boolean, Column, Date, Integer, String, Text, Time
from app.models.database import Base


class SearchProfile(Base):
    __tablename__ = "busqmp_search_profiles"

    id = Column(Integer, primary_key=True)
    owner_id = Column(String(64), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    industry = Column(String(250), nullable=False, default="")
    include_keywords = Column(Text, nullable=False, default="[]")
    exclude_keywords = Column(Text, nullable=False, default="[]")
    selected_categories = Column(Text, nullable=False, default="[]")
    opportunity_type = Column(String(50), nullable=False, default="all")
    region = Column(String(200), nullable=False, default="")
    organization = Column(String(500), nullable=False, default="")
    status = Column(String(100), nullable=False, default="")
    minimum_amount = Column(Integer, nullable=True)
    maximum_amount = Column(Integer, nullable=True)
    recipient_email = Column(String(320), nullable=False)
    delivery_time = Column(Time, nullable=False)
    timezone = Column(String(80), nullable=False, default="America/Santiago")
    enabled = Column(Boolean, nullable=False, default=True)
    last_sent_on = Column(Date, nullable=True)
