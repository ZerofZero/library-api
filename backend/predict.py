# predict.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from PIL import Image
import numpy as np
import io
from auth import verify_api_key

router = APIRouter(dependencies=[Depends(verify_api_key)])

GENRE_MAP = {
    0: "소설", 1: "에세이", 2: "역사", 3: "과학", 4: "예술",
    5: "자기계발", 6: "경제", 7: "시", 8: "만화", 9: "아동",
}

ml_models = {}


def softmax(x):
    exp_x = np.exp(x - np.max(x))
    return exp_x / exp_x.sum()


@router.post("/predict-genre")
async def predict_genre(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다")

    contents = await file.read()

    try:
        image = Image.open(io.BytesIO(contents)).convert("L")
    except Exception:
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다")

    image = image.resize((28, 28))
    image_array = np.array(image).astype(np.float32) / 255.0
    image_array = image_array.reshape(1, 1, 28, 28)

    session = ml_models.get("genre_classifier")
    if session is None:
        raise HTTPException(status_code=500, detail="모델이 로드되지 않았습니다")

    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: image_array})

    probabilities = softmax(outputs[0][0])
    predicted_class = int(np.argmax(probabilities))
    confidence = float(np.max(probabilities))

    genre = GENRE_MAP.get(predicted_class, "알 수 없음")

    return {
        "predicted_genre": genre,
        "confidence": confidence,
    }