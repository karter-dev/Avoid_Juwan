from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal, engine
from models import Base, Score
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# DB 초기화
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시 도메인 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 요청 스키마
class ScoreSubmission(BaseModel):
    user_id: str
    score: int

@app.post("/submit_score")
def submit_score(data: ScoreSubmission, db: Session = Depends(get_db)):
    existing = db.query(Score).filter(Score.user_id == data.user_id).first()
    if existing:
        if data.score > existing.score:
            existing.score = data.score
    else:
        new_score = Score(user_id=data.user_id, score=data.score)
        db.add(new_score)
    db.commit()
    return {"message": "Score submitted"}

@app.get("/get_rankings")
def get_rankings(db: Session = Depends(get_db)):
    scores = db.query(Score).order_by(Score.score.desc()).limit(10).all()
    return {"rankings": [{"user_id": s.user_id, "score": s.score} for s in scores]}

async def print_db_contents_periodically():
    while True:
        db = SessionLocal()
        try:
            rankings = db.query(Score).all()
            print("=== DB 랭킹 내용 ===")
            for r in rankings:
                print(f"user_id: {r.user_id}, score: {r.score}")
        finally:
            db.close()
        await asyncio.sleep(3)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(print_db_contents_periodically())
