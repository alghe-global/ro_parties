from typing import Annotated, List

from fastapi import FastAPI, Depends, status, Path, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import models
from database import SessionLocal, engine
from models import Party

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


DB_DEPENDENCY = Annotated[Session, Depends(get_db)]


class PartyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    deputies: int = Field(gt=-1)
    senators: int = Field(gt=-1)
    total: int = Field(gt=-1)


@app.get("/", status_code=status.HTTP_200_OK)
async def read_all(db: DB_DEPENDENCY):
    return db.query(Party).all()


PartiesPositiveIntId = Annotated[int, Field(gt=0)]


@app.get("/parties", status_code=status.HTTP_200_OK)
async def read_parties_configuration(
        db: DB_DEPENDENCY,
        party_ids: Annotated[List[PartiesPositiveIntId], Query()]
):
    parties = db.query(Party).all()
    if parties is None or len(parties) == 0:
        raise HTTPException(status_code=404, detail="No parties found")

    user_parties = set()

    for party_id in party_ids:
        party_model = db.query(Party).filter(Party.id == party_id).first()

        if party_model is None:
            raise HTTPException(
                status_code=404,
                detail="Party with id %d not found" % party_id
            )

        user_parties.add(party_model)

    parties_total = sum(user_party.total for user_party in user_parties)
    total = sum(party.total for party in parties)
    percentage = parties_total * 100 / total

    configuration = {
        "parties": user_parties,
        "parties_total": parties_total,
        "total": total,
        "percentage": percentage
    }

    return configuration


@app.get("/parties/{party_id}", status_code=status.HTTP_200_OK)
async def read_party(db: DB_DEPENDENCY, party_id: int = Path(gt=0)):
    party_model = db.query(Party).filter(Party.id == party_id).first()

    if party_model is None:
        raise HTTPException(status_code=404, detail="Party not found")

    return party_model


@app.post("/parties", status_code=status.HTTP_201_CREATED)
async def create_party(db: DB_DEPENDENCY, party_request: PartyRequest):
    party_model = Party(**party_request.model_dump())

    db.add(party_model)
    db.commit()


@app.put("/parties/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_party(
        db: DB_DEPENDENCY,
        party_request: PartyRequest,
        party_id: int = Path(gt=0)
):
    party_model = db.query(Party).filter(Party.id == party_id).first()

    if party_model is None:
        raise HTTPException(status_code=404, detail="Party not found")

    party_model.name = party_request.name
    party_model.deputies = party_request.deputies
    party_model.senators = party_request.senators
    party_model.total = party_request.total

    db.add(party_model)
    db.commit()


@app.delete("/parties/{party_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_party(db: DB_DEPENDENCY, party_id: int = Path(gt=0)):
    party_model = db.query(Party).filter(Party.id == party_id).first()

    if party_model is None:
        raise HTTPException(status_code=404, detail="Party not found")

    db.query(Party).filter(Party.id == party_id).delete()
    db.commit()