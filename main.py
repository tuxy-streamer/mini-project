from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


# pylint: disable=too-few-public-methods
class PredictionResponse(BaseModel):
    """Prediction response schema."""

    user_id: int
    confidence_score: float


@app.get("/attendance/recognise", response_model=PredictionResponse)
async def get_attendance_recognise():
    """Return attendance recognition data."""
    user_id: int = 123456789
    confidence_score: float = 77.4
    res: PredictionResponse = PredictionResponse(user_id, confidence_score)
    return res
