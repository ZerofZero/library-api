# routers/books.py
import random
import re
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from database import get_db
from models import BookModel
from auth import verify_api_key, verify_librarian_key
from config import settings

router = APIRouter(
    prefix="/books",
    tags=["books"],
    dependencies=[Depends(verify_api_key)],
)

LOAN_PERIOD_DAYS = 7
FINE_PER_DAY = 100


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    isbn: str = Field(min_length=10, max_length=13)


class BorrowRequest(BaseModel):
    borrower_name: str = Field(min_length=1, max_length=100)
    borrower_phone: str = Field(min_length=1, max_length=20)

    @field_validator("borrower_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[가-힣a-zA-Z\s]+$", v):
            raise ValueError("이름은 한글 또는 영문만 가능합니다")
        return v

    @field_validator("borrower_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^01[016789]-\d{3,4}-\d{4}$", v):
            raise ValueError("전화번호 형식이 올바르지 않습니다 (예: 010-1234-5678)")
        return v


class ReturnRequest(BaseModel):
    borrower_code: str | None = None


class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str | None
    is_borrowed: bool
    borrower_name: str | None
    borrower_phone: str | None
    due_date: datetime | None
    fine_paid: bool

    class Config:
        from_attributes = True


class BorrowResponse(BaseModel):
    id: int
    title: str
    author: str
    is_borrowed: bool
    borrower_name: str | None
    due_date: datetime | None
    borrower_code: str

    class Config:
        from_attributes = True


def get_book_or_404(book_id: int, db: Session = Depends(get_db)) -> BookModel:
    book = db.query(BookModel).filter(BookModel.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="해당 도서를 찾을 수 없습니다.")
    return book


def calculate_fine(book: BookModel) -> int:
    if not book.is_borrowed or book.due_date is None:
        return 0
    overdue_days = (datetime.utcnow() - book.due_date).days
    if overdue_days <= 0:
        return 0
    return overdue_days * FINE_PER_DAY


@router.get("", response_model=list[BookResponse])
def get_books(db: Session = Depends(get_db)):
    return db.query(BookModel).all()


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book: BookModel = Depends(get_book_or_404)):
    return book


@router.post("", status_code=201, response_model=BookResponse, dependencies=[Depends(verify_librarian_key)])
def create_book(book: BookCreate, db: Session = Depends(get_db)):
    new_book = BookModel(
        title=book.title,
        author=book.author,
        isbn=book.isbn,
    )
    db.add(new_book)
    db.commit()
    db.refresh(new_book)
    return new_book


@router.patch("/{book_id}/borrow", response_model=BorrowResponse)
def borrow_book(
    borrow: BorrowRequest,
    book: BookModel = Depends(get_book_or_404),
    db: Session = Depends(get_db),
):
    if book.is_borrowed:
        raise HTTPException(status_code=400, detail="이미 대출 중인 도서입니다")

    code = "".join(random.choices(string.digits, k=6))

    book.is_borrowed = True
    book.borrower_name = borrow.borrower_name
    book.borrower_phone = borrow.borrower_phone
    book.borrower_code = code
    book.borrowed_at = datetime.utcnow()
    book.due_date = datetime.utcnow() + timedelta(days=LOAN_PERIOD_DAYS)
    book.fine_paid = False

    db.commit()
    db.refresh(book)
    return book


@router.patch("/{book_id}/return", response_model=BookResponse)
def return_book(
    return_req: ReturnRequest,
    book: BookModel = Depends(get_book_or_404),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key),
):
    if not book.is_borrowed:
        raise HTTPException(status_code=400, detail="대출 중이 아닌 도서입니다")

    is_librarian = api_key in settings.librarian_keys_list

    if not is_librarian:
        if return_req.borrower_code != book.borrower_code:
            raise HTTPException(status_code=403, detail="본인 확인에 실패했습니다")

    fine = calculate_fine(book)
    if fine > 0 and not book.fine_paid:
        raise HTTPException(status_code=400, detail=f"연체료 {fine}원을 먼저 납부해야 합니다")

    book.is_borrowed = False
    book.borrower_name = None
    book.borrower_phone = None
    book.borrower_code = None
    book.borrowed_at = None
    book.due_date = None
    book.fine_paid = True

    db.commit()
    db.refresh(book)
    return book


@router.patch("/{book_id}/pay-fine", response_model=BookResponse)
def pay_fine(
    book: BookModel = Depends(get_book_or_404),
    db: Session = Depends(get_db),
):
    if not book.is_borrowed:
        raise HTTPException(status_code=400, detail="대출 중이 아닌 도서입니다")
    book.fine_paid = True
    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", dependencies=[Depends(verify_librarian_key)])
def delete_book(
    book: BookModel = Depends(get_book_or_404),
    db: Session = Depends(get_db),
):
    db.delete(book)
    db.commit()
    return {"message": f"'{book.title}' 삭제 완료"}