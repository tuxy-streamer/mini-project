import io
import logging
import os
import pickle
from collections import defaultdict
from typing import List, Optional, Tuple

import face_recognition
import numpy as np

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def encode_images(user_id: int, image_paths: List[str]) -> List[Tuple[int, np.ndarray]]:
    encodings: List[Tuple[int, np.ndarray]] = []
    for path in image_paths:
        logger.info(f"Encoding image: {path}")
        image = face_recognition.load_image_file(path)
        face_encs = face_recognition.face_encodings(image)
        if face_encs:
            encodings.append((user_id, face_encs[0]))
            logger.info(f"Encoded face for user_id {user_id}")
        else:
            logger.warning(f"No faces found in image: {path}")
    logger.info(f"Total encodings generated: {len(encodings)}")
    return encodings


def save_encodings(
    new_encodings: List[Tuple[int, np.ndarray]],
    filepath: str = "encodings.pkl",
    overwrite: bool = False,
) -> None:
    if not overwrite and os.path.exists(filepath):
        logger.info(f"Loading existing encodings from {filepath} to append new ones")
        with open(filepath, "rb") as f:
            existing_encodings = pickle.load(f)
        updated_encodings = existing_encodings + new_encodings
    else:
        updated_encodings = new_encodings
        logger.info(f"Overwriting encodings file: {filepath}")

    with open(filepath, "wb") as f:
        pickle.dump(updated_encodings, f)

    logger.info(
        f"Encodings saved to {filepath}. Total entries: {len(updated_encodings)}"
    )


def load_encodings(filepath: str = "encodings.pkl") -> List[Tuple[int, np.ndarray]]:
    encs = []
    with open(filepath, "rb") as f:
        encs = pickle.load(f)
    for user_id, _ in encs:
        print(f"Loaded user_id: {user_id} ({type(user_id)})")
    return encs

def classify_face_from_bytes_list(
    images_bytes_list: List[bytes],
    known_encodings: List[Tuple[int, np.ndarray]],
    tolerance: float = 0.6,
) -> Optional[Tuple[int, float]]:
    logger.info(
        f"Classifying {len(images_bytes_list)} images with tolerance {tolerance}"
    )
    confidence_map = defaultdict(list)

    user_ids = [user_id for user_id, _ in known_encodings]
    encodings = [enc for _, enc in known_encodings]

    for idx, image_bytes in enumerate(images_bytes_list):
        logger.info(f"Processing image {idx + 1}/{len(images_bytes_list)}")
        image = face_recognition.load_image_file(io.BytesIO(image_bytes))
        unknown_encs = face_recognition.face_encodings(image)
        if not unknown_encs:
            logger.warning(f"No faces found in image {idx + 1}")
            continue

        unknown_enc = unknown_encs[0]

        distances = face_recognition.face_distance(encodings, unknown_enc)
        best_match_index = np.argmin(distances)
        best_distance = distances[best_match_index]

        if best_distance <= tolerance:
            user_id = user_ids[best_match_index]
            confidence = round((1.0 - best_distance / tolerance) * 100, 2)
            logger.info(
                f"Image {idx + 1} matched user_id {user_id} with confidence {confidence}%"
            )
            confidence_map[user_id].append(confidence)
        else:
            logger.info(
                f"Image {idx + 1} no good match found (best distance {best_distance:.3f})"
            )

    if not confidence_map:
        logger.info("No matches found in any images")
        return None

    avg_confidences = {
        uid: sum(scores) / len(scores) for uid, scores in confidence_map.items()
    }
    for uid, avg_conf in avg_confidences.items():
        logger.info(f"user_id {uid} average confidence: {avg_conf:.2f}%")

    best_user_id = max(avg_confidences, key=avg_confidences.get)
    best_confidence = avg_confidences[best_user_id]
    logger.info(
        f"Best match: user_id {best_user_id} with average confidence {best_confidence:.2f}%"
    )

    return best_user_id, best_confidence
