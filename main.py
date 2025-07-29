from typing import List

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

app = FastAPI()


# pylint: disable=too-few-public-methods
class PredictionResponse(BaseModel):
    """Prediction response schema."""

    user_id: int
    confidence_score: float


res: PredictionResponse = PredictionResponse(user_id=0, confidence_score=0.0)


def user_id_prediction(frames: List[UploadFile]):
    """Mutate server response with model prediction."""


@app.get("/attendance/recognise", response_model=PredictionResponse)
async def get_attendance_recognise():
    """Return attendance recognition data."""
    return res


@app.post("/attendance/recognise")
async def post_attendance_model(frames: List[UploadFile] = File(...)):
    """Get the frames for recognition."""
    user_id_prediction(frames)
    return {"status": "success"}
