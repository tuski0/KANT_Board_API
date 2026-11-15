"""
실행 중인 서버에 요청을 보내 주요 시나리오를 확인하는 스크립트

사용법:
    uv run --with httpx python scripts/smoke_test.py [BASE_URL]
    (BASE_URL 기본값: http://localhost:8000, 관리자 계정은 .env 의 ADMIN_EMAIL / ADMIN_PASSWORD)
"""
import os
import sys
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()
BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
client = httpx.Client(base_url=BASE, timeout=10)

passed = failed = 0


def check(name: str, res: httpx.Response, expected: int):
    global passed, failed
    ok = res.status_code == expected
    passed += ok
    failed += not ok
    mark = "PASS" if ok else "FAIL"
    detail = ""
    if res.content and res.headers.get("content-type", "").startswith("application/json"):
        body = res.json()
        if isinstance(body, dict) and body.get("success") is False:
            detail = f"  -> {body.get('code')}: {body.get('message')}"
    print(f"[{mark}] {res.status_code} (기대 {expected}) {name}{detail}")
    return res


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(email: str, password: str) -> str:
    res = client.post("/v1/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]


suffix = uuid.uuid4().hex[:6]
A = {"email": f"alice_{suffix}@example.com", "name": "앨리스", "password": "Passw0rd!"}
B = {"email": f"bob_{suffix}@example.com", "name": "밥밥", "password": "Passw0rd!"}

print("== 1. 회원가입 ==")
check("회원 A 가입", client.post("/v1/users", json=A), 201)
check("회원 B 가입", client.post("/v1/users", json=B), 201)
check("같은 이메일 재가입 → 409", client.post("/v1/users", json=A), 409)
check("약한 비밀번호 → 422", client.post("/v1/users", json={**A, "email": f"x_{suffix}@example.com", "password": "12345678"}), 422)
check("이메일 형식 오류 → 422", client.post("/v1/users", json={**A, "email": "not-email"}), 422)

print("\n== 2. 로그인 (JWT) ==")
check("틀린 비밀번호 → 401", client.post("/v1/auth/login", json={"email": A["email"], "password": "Wrong123!"}), 401)
token_a, token_b = login(A["email"], A["password"]), login(B["email"], B["password"])
token_admin = login(os.environ["ADMIN_EMAIL"], os.environ["ADMIN_PASSWORD"])
check("내 정보 조회", client.get("/v1/users/me", headers=auth(token_a)), 200)
check("토큰 없이 내 정보 → 401", client.get("/v1/users/me"), 401)
check("위조 토큰 → 401", client.get("/v1/users/me", headers=auth("abc.def.ghi")), 401)

print("\n== 3. 게시글 CRUD + 작성자 검증 ==")
check("비로그인 글쓰기 → 401", client.post("/v1/boards/free/posts", json={"title": "t", "content": "c"}), 401)
res = check("A 글쓰기", client.post("/v1/boards/free/posts", json={"title": f"테스트 글 {suffix}", "content": "본문"}, headers=auth(token_a)), 201)
post_id = res.json()["post_id"]
check("제목 누락 → 422", client.post("/v1/boards/free/posts", json={"content": "c"}, headers=auth(token_a)), 422)
check("비로그인 목록 조회", client.get("/v1/boards/free/posts"), 200)
check("검색 (TITLE)", client.get("/v1/boards/free/posts", params={"search_type": "TITLE", "keyword": suffix}), 200)
check("비로그인 상세 조회", client.get(f"/v1/posts/{post_id}"), 200)
check("없는 글 → 404", client.get("/v1/posts/999999"), 404)
check("없는 게시판 → 404", client.get("/v1/boards/nope/posts"), 404)
check("B가 A 글 수정 → 403", client.put(f"/v1/posts/{post_id}", json={"title": "x", "content": "x"}, headers=auth(token_b)), 403)
check("A가 본인 글 수정", client.put(f"/v1/posts/{post_id}", json={"title": "수정된 제목", "content": "수정된 본문"}, headers=auth(token_a)), 200)
check("관리자가 A 글 수정", client.put(f"/v1/posts/{post_id}", json={"title": "관리자 수정", "content": "관리자"}, headers=auth(token_admin)), 200)

print("\n== 4. 댓글 ==")
check("비로그인 댓글 → 401", client.post(f"/v1/posts/{post_id}/comments", json={"content": "hi"}), 401)
res = check("B 댓글 작성", client.post(f"/v1/posts/{post_id}/comments", json={"content": "B의 댓글"}, headers=auth(token_b)), 201)
comment_id = res.json()["comment_id"]
check("A가 B 댓글 수정 → 403", client.put(f"/v1/comments/{comment_id}", json={"content": "x"}, headers=auth(token_a)), 403)
check("B가 본인 댓글 수정", client.put(f"/v1/comments/{comment_id}", json={"content": "B 수정"}, headers=auth(token_b)), 200)
check("댓글 목록", client.get(f"/v1/posts/{post_id}/comments"), 200)
check("B 댓글 삭제", client.delete(f"/v1/comments/{comment_id}", headers=auth(token_b)), 204)

print("\n== 5. 게시판 관리 (관리자 전용) ==")
new_board = {"board_id": f"qna{suffix}", "board_name": "질문게시판"}
check("일반 회원 게시판 생성 → 403", client.post("/v1/boards", json=new_board, headers=auth(token_a)), 403)
check("관리자 게시판 생성", client.post("/v1/boards", json=new_board, headers=auth(token_admin)), 201)
check("글쓰기 권한 ALL(비회원) → 422",
      client.post("/v1/boards", json={"board_id": f"bad{suffix}", "board_name": "x", "authority": {"edit_role": "ALL"}}, headers=auth(token_admin)), 422)
check("관리자 게시판 삭제", client.delete(f"/v1/boards/{new_board['board_id']}", headers=auth(token_admin)), 204)

print("\n== 6. 삭제 / 로그아웃 / 탈퇴 ==")
check("B가 A 글 삭제 → 403", client.delete(f"/v1/posts/{post_id}", headers=auth(token_b)), 403)
check("A 본인 글 삭제", client.delete(f"/v1/posts/{post_id}", headers=auth(token_a)), 204)
check("삭제된 글 조회 → 404", client.get(f"/v1/posts/{post_id}"), 404)
check("A 로그아웃", client.post("/v1/auth/logout", headers=auth(token_a)), 204)
check("로그아웃한 토큰 재사용 → 401", client.get("/v1/users/me", headers=auth(token_a)), 401)
check("B 비밀번호 변경", client.patch("/v1/users/me/password", json={"old_password": B["password"], "new_password": "NewPassw0rd!"}, headers=auth(token_b)), 200)
check("B 탈퇴", client.delete("/v1/users/me", headers=auth(token_b)), 200)
check("탈퇴한 B 로그인 → 401", client.post("/v1/auth/login", json={"email": B["email"], "password": "NewPassw0rd!"}), 401)

print(f"\n결과: {passed} 통과 / {failed} 실패")
sys.exit(1 if failed else 0)
