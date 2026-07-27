# frontend/streamlit_app.py
import re
import os
import streamlit as st
import requests


def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.environ.get(key, default)


st.title("도서 대출 관리 + 장르 예측")

API_URL = get_secret("BACKEND_URL", "http://localhost:8000")
API_KEY = get_secret("API_KEY", "my-secret-key-12345")
LIBRARIAN_KEY = get_secret("LIBRARIAN_KEY", "librarian-key-99999")

headers = {"X-API-Key": API_KEY}
librarian_headers = {"X-API-Key": LIBRARIAN_KEY}


def format_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)[:11]
    if len(digits) < 4:
        return digits
    elif len(digits) < 8:
        return f"{digits[:3]}-{digits[3:]}"
    else:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"


tab1, tab2, tab3 = st.tabs(["도서 목록", "대출/반납", "장르 예측"])

# ── 탭 1: 도서 목록 조회 + 등록 (사서 전용) ──
with tab1:
    st.subheader("도서 등록 (사서 전용)")
    with st.form("create_book_form"):
        title = st.text_input("제목")
        author = st.text_input("저자")
        isbn = st.text_input("ISBN (10~13자리)")
        submitted = st.form_submit_button("등록")

        if submitted:
            if not title or not author or not isbn:
                st.error("제목, 저자, ISBN은 모두 필수입니다")
            else:
                response = requests.post(
                    f"{API_URL}/books",
                    headers=librarian_headers,
                    json={"title": title, "author": author, "isbn": isbn},
                )
                if response.status_code == 201:
                    st.success("도서가 등록되었습니다")
                elif response.status_code == 403:
                    st.error("사서 권한이 필요합니다")
                else:
                    st.error(f"등록 실패: {response.status_code} - {response.json().get('detail', '')}")

    st.subheader("도서 목록")
    response = requests.get(f"{API_URL}/books", headers=headers)
    if response.status_code == 200:
        st.json(response.json())
    else:
        st.error(f"연결 실패: {response.status_code}")

# ── 탭 2: 대출/반납 ──
with tab2:
    response = requests.get(f"{API_URL}/books", headers=headers)
    if response.status_code == 200:
        books = response.json()
        if not books:
            st.info("등록된 도서가 없습니다")
        else:
            book_options = {
                f"{b['id']} - {b['title']} ({'대출중' if b['is_borrowed'] else '대출가능'})": b
                for b in books
            }
            selected_label = st.selectbox("도서 선택", list(book_options.keys()))
            selected_book = book_options[selected_label]

            if selected_book["is_borrowed"]:
                st.write(f"현재 대출자: {selected_book['borrower_name']}")
                st.write(f"반납 기한: {selected_book['due_date']}")

                st.markdown("**본인 확인 후 반납**")
                borrower_code = st.text_input("반납 코드 (6자리)", key="return_code")
                if st.button("반납 처리 (본인)"):
                    r = requests.patch(
                        f"{API_URL}/books/{selected_book['id']}/return",
                        headers=headers,
                        json={"borrower_code": borrower_code},
                    )
                    if r.status_code == 200:
                        st.success("반납 처리되었습니다")
                        st.rerun()
                    else:
                        st.error(f"반납 실패: {r.status_code} - {r.json().get('detail', '')}")

                st.markdown("---")
                st.markdown("**사서 전용 처리**")
                if st.button("반납 처리 (사서 - 본인확인 우회)"):
                    r = requests.patch(
                        f"{API_URL}/books/{selected_book['id']}/return",
                        headers=librarian_headers,
                        json={},
                    )
                    if r.status_code == 200:
                        st.success("사서 권한으로 반납 처리되었습니다")
                        st.rerun()
                    else:
                        st.error(f"반납 실패: {r.status_code} - {r.json().get('detail', '')}")

                if st.button("연체료 납부 처리"):
                    r = requests.patch(
                        f"{API_URL}/books/{selected_book['id']}/pay-fine",
                        headers=headers,
                    )
                    if r.status_code == 200:
                        st.success("연체료 납부 처리되었습니다")
                        st.rerun()
                    else:
                        st.error(f"처리 실패: {r.status_code}")

            else:
                borrower_name = st.text_input("대출자 이름 (한글 또는 영문)", placeholder="예: 홍길동")
                borrower_phone_raw = st.text_input("대출자 전화번호 (숫자만 입력)", placeholder="예: 01012345678")
                borrower_phone = format_phone(borrower_phone_raw)
                if borrower_phone_raw:
                    st.caption(f"입력된 번호: {borrower_phone}")

                if st.button("대출 처리"):
                    if not borrower_name or not borrower_phone:
                        st.error("대출자 이름과 전화번호를 모두 입력하세요")
                    else:
                        r = requests.patch(
                            f"{API_URL}/books/{selected_book['id']}/borrow",
                            headers=headers,
                            json={"borrower_name": borrower_name, "borrower_phone": borrower_phone},
                        )
                        if r.status_code == 200:
                            result = r.json()
                            st.success("대출 처리되었습니다")
                            st.warning(
                                f"반납 시 필요한 본인 확인 코드: **{result['borrower_code']}**\n\n"
                                f"이 코드는 다시 보여지지 않으니 꼭 기억해두세요."
                            )
                        elif r.status_code == 422:
                            errors = r.json().get("detail", [])
                            for err in errors:
                                st.error(err.get("msg", "입력값이 올바르지 않습니다"))
                        else:
                            st.error(f"대출 실패: {r.status_code} - {r.json().get('detail', '')}")
    else:
        st.error(f"연결 실패: {response.status_code}")

# ── 탭 3: 장르 예측 ──
with tab3:
    uploaded = st.file_uploader("표지 이미지를 업로드하세요", type=["png", "jpg"])
    if uploaded:
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        response = requests.post(
            f"{API_URL}/predict-genre",
            headers=headers,
            files=files,
        )
        if response.status_code == 200:
            result = response.json()
            st.success(
                f"예측 장르: {result['predicted_genre']} "
                f"(확신도 {result['confidence']*100:.1f}%)"
            )
        else:
            st.error(f"예측 실패: {response.status_code}")