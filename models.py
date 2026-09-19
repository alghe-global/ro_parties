from database import Base
from sqlalchemy import Column, Integer, String


class Party(Base):
    __tablename__ = "parties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    deputies = Column(Integer)
    senators = Column(Integer)
    total = Column(Integer)