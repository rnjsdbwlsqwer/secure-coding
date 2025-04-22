# 🛒 Secure Coding Market Platform

Flask 기반으로 제작된 **중고 거래 웹 플랫폼**입니다.  
실시간 채팅, 상품 검색, 송금, 관리자 제어 등 다양한 기능을 포함하고 있습니다.

---

## 🔧 주요 기능

### 1. 👤 유저 관리
- 회원가입 / 로그인 / 로그아웃
- 마이페이지 (소개글 및 비밀번호 수정)
- 사용자 정보 DB 저장

### 2. 📦 상품 관리
- 상품 등록 / 조회 / 상세 페이지
- 카테고리, 조회수 관리
- 상품 삭제 기능 (관리자용)

### 3. 💬 유저 소통 기능
- 실시간 전체 채팅
- 1:1 개인 채팅 기능

### 4. 🚨 악성 유저 필터링
- 유저 및 상품 신고
- 관리자 불량 상품 삭제
- 관리자 유저 휴면 처리

### 5. 💰 송금 기능
- 사용자 간 금액 송금
- 잔액 충전 기능
- 거래 내역 확인

### 6. 🔍 상품 검색 기능
- 키워드 검색
- 정렬 기능 (최신순, 가격순, 인기순)
- 카테고리 필터

### 7. 🛠 관리자 페이지
- 전체 유저/상품/거래내역 관리
- 불량 유저 및 콘텐츠 제어

---

## 🛠 기술 스택

- **백엔드**: Python, Flask
- **템플릿**: Jinja2, HTML5
- **DB**: SQLite3
- **실시간 통신**: Flask-SocketIO
- **프론트엔드 프레임워크**: Bootstrap 5
- **버전 관리**: Git, GitHub

---

## 🚀 실행 방법

1. 프로젝트 클론
```bash
git clone https://github.com/your-username/secure-coding.git
cd secure-coding

2. 가상환경 설정 & 패키지 설치
python -m venv venv
source venv/bin/activate  # Windows는 venv\Scripts\activate
pip install -r requirements.txt

3. 서버 실행
python app.py
# 또는
flask run

4. 접속
http://localhost:5000 에 접속하여 확인

## 🙋 관리자 계정 사용 안내
관리자 ID: admin
이 계정으로 로그인 시 관리자 페이지 접근 가능
→ /admin

## 📂 프로젝트 구조 예시
secure-coding/
├── app.py
├── market.db
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   └── ...
├── static/
├── .gitignore
└── README.md

