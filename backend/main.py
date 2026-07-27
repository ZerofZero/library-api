# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import onnxruntime as ort

from database import engine, Base
from routers import books
from predict import router as predict_router, ml_models
from config import settings

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 서버 "시작" 시 딱 한 번 실행 ──
    print("모델 로드 중...")
    ml_models["genre_classifier"] = ort.InferenceSession("mnist_model.onnx")
    print("장르 예측 모델 로드 완료")

    yield  # ← 이 지점부터 서버가 요청을 받기 시작

    # ── 서버 "종료" 시 딱 한 번 실행 ──
    ml_models.clear()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)

app.include_router(books.router)
app.include_router(predict_router)


@app.get("/")
def read_root():
    return {"message": "안녕하세요, 도서 대출 관리 API입니다!"}