# models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base

class BookModel(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100), nullable=False)
    isbn = Column(String(20), nullable=True)

    is_borrowed = Column(Boolean, default=False)
    borrower_name = Column(String(100), nullable=True)
    borrower_phone = Column(String(20), nullable=True)
    borrower_code = Column(String(6), nullable=True)

    borrowed_at = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)

    fine_paid = Column(Boolean, default=True)