from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime

Base = declarative_base()

class Keyword(Base):
    __tablename__ = "keywords"
    id = Column(Integer, primary_key=True, autoincrement=True)
    seed = Column(String(255), nullable=True)
    keyword = Column(String(255), nullable=False, unique=True, index=True)
    volume = Column(Float, nullable=True)
    competition = Column(Float, nullable=True)
    cpc = Column(Float, nullable=True)
    trend = Column(Float, nullable=True)
    score = Column(Float, nullable=True)
    difficulty = Column(String(50), nullable=True)
    intent = Column(String(50), nullable=True)
    competitors = Column(Text, nullable=True)  # JSON string
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IntentCache(Base):
    __tablename__ = "intent_cache"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(255), nullable=False, unique=True, index=True)
    intent = Column(String(50), nullable=False)
