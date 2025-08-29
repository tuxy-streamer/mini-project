import io
import os
import logging
from typing import List

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from PIL import Image
from pydantic import BaseModel

from model.model import (
    classify_face_from_bytes_list,
    encode_images,
    load_encodings,
    save_encodings,
)

app = FastAPI()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
db_url = os.getenv("DB_URL")
db = psycopg2.connect(db_url)
db.autocommit = True


class PredictionResponse(BaseModel):
    """Prediction response schema."""

    user_id: int
    confidence_score: float


res: PredictionResponse = PredictionResponse(user_id=0, confidence_score=0.0)


class RegisterPayload(BaseModel):
    status: str
    user_id: int


def default_prediction_response() -> None:
    """Reset prediction response."""
    global res
    res = PredictionResponse(user_id=0, confidence_score=0.0)
    logger.info("Prediction response reset to default.")


async def user_id_prediction(frames: List[UploadFile]) -> PredictionResponse:
    logger.info(f"Starting user_id_prediction with {len(frames)} frames.")
    known_encodings = load_encodings("encodings.pkl")
    logger.info(f"Loaded {len(known_encodings)} known encodings.")

    images_bytes = []
    for idx, frame in enumerate(frames):
        img_bytes = await frame.read()
        images_bytes.append(img_bytes)
        logger.info(f"Read frame {idx} ({len(img_bytes)} bytes)")

    prediction = classify_face_from_bytes_list(images_bytes, known_encodings)
    if prediction is None:
        logger.info("No matching faces found in prediction.")
        return PredictionResponse(user_id=0, confidence_score=0.0)

    user_id, confidence = prediction
    logger.info(f"Prediction result - user_id: {user_id}, confidence: {confidence:.2f}%")
    return PredictionResponse(user_id=user_id, confidence_score=confidence)


def get_frames(user_id: int) -> None:
    logger.info(f"Fetching frames from DB for user_id: {user_id}")
    query = "SELECT frame_bytes FROM frames WHERE user_id = %s ORDER BY created_at ASC;"
    with db.cursor() as cur:
        cur.execute(query, (user_id,))
        rows = cur.fetchall()

    folder_path = os.path.join("training", str(user_id))
    os.makedirs(folder_path, exist_ok=True)
    logger.info(f"Saving {len(rows)} frames to {folder_path}")

    for idx, (frame_bytes,) in enumerate(rows):
        img = Image.open(io.BytesIO(frame_bytes))
        img_path = os.path.join(folder_path, f"frame_{idx}.png")
        img.save(img_path)
        logger.info(f"Saved frame {idx} to {img_path}")

    frame_path_list: List[str] = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(".png")
    ]
    logger.info(f"Encoding {len(frame_path_list)} images from {folder_path}")

    encodings = encode_images(user_id, frame_path_list)
    logger.info(f"Generated {len(encodings)} face encodings.")

    save_encodings(encodings)
    logger.info("Encodings saved to file.")


@app.get("/attendance/recognise", response_model=PredictionResponse)
async def get_attendance_recognise():
    """Return attendance recognition data."""
    global res
    logger.info("GET /attendance/recognise called")
    return res


@app.post("/attendance/recognise")
async def post_attendance_model(frames: List[UploadFile] = File(...)):
    """Get the frames for recognition."""
    print(frames)
    global res
    logger.info(f"POST /attendance/recognise called with {len(frames)} frames")
    default_prediction_response()
    res = await user_id_prediction(frames)
    return res


@app.post("/register/success")
async def post_register_success(payload: RegisterPayload):
    """Get the new user creation status."""
    logger.info(f"POST /register/success called with payload: {payload}")
    if payload.status == "success":
        get_frames(payload.user_id)
    return {"status": "success"}
