from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class DummyInput(BaseModel):
    dummy: str

@app.post("/recognise")
async def recognise(input_data: DummyInput):
    return {"id": 123456789}