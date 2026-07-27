# test_main.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
HEADERS = {"X-API-Key": "my-secret-key-12345"}
LIBRARIAN_HEADERS = {"X-API-Key": "librarian-key-99999"}


def test_get_books_without_api_key():
    """API 키 없이 요청하면 401이 나와야 한다"""
    response = client.get("/books")
    assert response.status_code == 401


def test_create_book_without_librarian_key():
    """일반 키로 도서 등록을 시도하면 403이 나와야 한다"""
    response = client.post(
        "/books",
        headers=HEADERS,
        json={"title": "권한 테스트", "author": "테스터", "isbn": "1234567890"},
    )
    assert response.status_code == 403


def test_create_book():
    """사서 키로 도서 등록이 정상 동작해야 한다"""
    response = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "파이썬 완전정복", "author": "홍길동", "isbn": "9788900000000"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "파이썬 완전정복"
    assert data["is_borrowed"] is False


def test_create_book_with_empty_title():
    """제목이 빈 문자열이면 422가 나와야 한다"""
    response = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "", "author": "홍길동", "isbn": "1234567890"},
    )
    assert response.status_code == 422


def test_borrow_with_invalid_phone_fails():
    """전화번호 형식이 틀리면 422가 나와야 한다"""
    create_res = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "전화번호 검증 테스트 도서", "author": "테스터", "isbn": "6666666666"},
    )
    book_id = create_res.json()["id"]

    borrow_res = client.patch(
        f"/books/{book_id}/borrow",
        headers=HEADERS,
        json={"borrower_name": "김철수", "borrower_phone": "01012345678"},  # 하이픈 없음
    )
    assert borrow_res.status_code == 422


def test_borrow_with_invalid_name_fails():
    """이름에 자음/모음만 있으면 422가 나와야 한다"""
    create_res = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "이름 검증 테스트 도서", "author": "테스터", "isbn": "7777777777"},
    )
    book_id = create_res.json()["id"]

    borrow_res = client.patch(
        f"/books/{book_id}/borrow",
        headers=HEADERS,
        json={"borrower_name": "ㄷ휴ㅅ", "borrower_phone": "010-1234-5678"},
    )
    assert borrow_res.status_code == 422


def test_borrow_returns_code_and_double_borrow_fails():
    """정상 대출 시 borrower_code가 발급되고, 중복 대출은 400이 나와야 한다"""
    create_res = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "테스트 도서", "author": "테스터", "isbn": "1111111111"},
    )
    book_id = create_res.json()["id"]

    borrow_res = client.patch(
        f"/books/{book_id}/borrow",
        headers=HEADERS,
        json={"borrower_name": "김철수", "borrower_phone": "010-1234-5678"},
    )
    assert borrow_res.status_code == 200
    data = borrow_res.json()
    assert data["is_borrowed"] is True
    assert "borrower_code" in data
    assert len(data["borrower_code"]) == 6

    double_borrow_res = client.patch(
        f"/books/{book_id}/borrow",
        headers=HEADERS,
        json={"borrower_name": "이영희", "borrower_phone": "010-9999-9999"},
    )
    assert double_borrow_res.status_code == 400


def test_return_with_wrong_code_fails():
    """잘못된 코드로 반납을 시도하면 403이 나와야 한다"""
    create_res = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "본인확인 테스트 도서", "author": "테스터", "isbn": "2222222222"},
    )
    book_id = create_res.json()["id"]

    client.patch(
        f"/books/{book_id}/borrow",
        headers=HEADERS,
        json={"borrower_name": "박영수", "borrower_phone": "010-1111-2222"},
    )

    return_res = client.patch(
        f"/books/{book_id}/return",
        headers=HEADERS,
        json={"borrower_code": "000000"},
    )
    assert return_res.status_code == 403


def test_return_with_correct_code_succeeds():
    """정확한 코드로 반납하면 200이 나와야 한다"""
    create_res = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "정상 반납 테스트 도서", "author": "테스터", "isbn": "3333333333"},
    )
    book_id = create_res.json()["id"]

    borrow_res = client.patch(
        f"/books/{book_id}/borrow",
        headers=HEADERS,
        json={"borrower_name": "최민지", "borrower_phone": "010-3333-4444"},
    )
    code = borrow_res.json()["borrower_code"]

    return_res = client.patch(
        f"/books/{book_id}/return",
        headers=HEADERS,
        json={"borrower_code": code},
    )
    assert return_res.status_code == 200
    assert return_res.json()["is_borrowed"] is False


def test_librarian_can_return_without_code():
    """사서 키는 코드 없이도 반납 처리가 가능해야 한다"""
    create_res = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "사서 우회 테스트 도서", "author": "테스터", "isbn": "4444444444"},
    )
    book_id = create_res.json()["id"]

    client.patch(
        f"/books/{book_id}/borrow",
        headers=HEADERS,
        json={"borrower_name": "정다은", "borrower_phone": "010-5555-6666"},
    )

    return_res = client.patch(
        f"/books/{book_id}/return",
        headers=LIBRARIAN_HEADERS,
        json={},
    )
    assert return_res.status_code == 200


def test_return_not_borrowed_book():
    """대출 중이 아닌 책을 반납하려 하면 400이 나와야 한다"""
    create_res = client.post(
        "/books",
        headers=LIBRARIAN_HEADERS,
        json={"title": "반납 테스트 도서", "author": "테스터", "isbn": "5555555555"},
    )
    book_id = create_res.json()["id"]

    return_res = client.patch(f"/books/{book_id}/return", headers=HEADERS, json={})
    assert return_res.status_code == 400


def test_get_nonexistent_book():
    """존재하지 않는 book_id 조회 시 404가 나와야 한다"""
    response = client.get("/books/99999", headers=HEADERS)
    assert response.status_code == 404