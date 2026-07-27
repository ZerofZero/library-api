# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DB 위치 경로
DATABASE_URL = "sqlite:///./library.db"

# 엔진 생성
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델 연결
Base = declarative_base()  # 테이블 모델이 상속받을 기본 클래스

# 다른 파일에서 DB 세션을 가져다 쓸 수 있게 해주는 함수 -> 의존성 주입
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()