from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


# pylint: disable=too-few-public-methods
class PredictionResponse(BaseModel):
    """Prediction response schema."""

    user_id: int
    confidence_score: float


res: PredictionResponse = PredictionResponse(user_id=0, confidence_score=0.0)

@app.get("/attendance/recognise", response_model=PredictionResponse)
async def get_attendance_recognise():
    """Return attendance recognition data."""
    return res
