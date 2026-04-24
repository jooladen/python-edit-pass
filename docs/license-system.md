# 라이선스 시스템 설계 문서
https://inspier.co.kr/download.php

## 1. 전체 구조

```
Python 소스 (.py)
    ↓ PyInstaller
단일 실행파일 (.exe)
    ↓ Inno Setup
설치 프로그램 (setup.exe)
    └─ 첫 실행 시 라이선스 활성화 창 표시
    └─ 서버 검증 통과 → license.dat 저장
    └─ 이후 실행 시 token 재확인 → 메인 앱 진입

클라이언트 (exe)                서버 (FastAPI)
─────────────────────────────────────────────
Activate 클릭
→ POST /api/activate            → 키 DB 조회
  { key, hwid }                → 사용 횟수 체크
                                → HWID 바인딩 저장
                               ← { ok: true, token: "..." }
token 암호화 저장 (license.dat)
```

---

## 2. GUI 프레임워크 선택

| 항목 | tkinter | customtkinter | PyQt6 |
|------|---------|---------------|-------|
| 설치 | 기본 내장 | `pip install customtkinter` | `pip install PyQt6` |
| 스타일 | 구식 | **모던 (Win11 느낌)** | 매우 세련 |
| 난이도 | 쉬움 | 쉬움 | 중간 |
| 패키징 용량 | 작음 | 작음 | ~30MB |
| 추천 상황 | 간단 도구 | **이 프로젝트** | 전문 상용 앱 |

**결론**: customtkinter 사용. 스크린샷(inspier)과 동일한 스타일.

---

## 3. 라이선스 활성화 다이얼로그

### UI 구성 요소
- 방패 아이콘 (상단 중앙)
- 앱 이름 (Bold)
- 부제목 "Enter your license key"
- 키 입력 필드 (placeholder: `NSP-XXXX-XXXX-XXXX`)
- Exit 버튼 (외곽선)
- Activate 버튼 (채움, 파란색)

### 방패 아이콘 구현 방법

```python
# 방법 A: PNG 파일 로드 (권장)
from PIL import Image
from customtkinter import CTkImage, CTkLabel

icon = CTkImage(Image.open("assets/shield.png"), size=(64, 64))
CTkLabel(app, image=icon, text="").pack()

# 방법 B: Unicode 이모지 (의존성 0)
CTkLabel(app, text="🛡", font=("Segoe UI Emoji", 48)).pack()
```

### 첫 실행 분기 로직

```python
from pathlib import Path

if not Path("license.dat").exists():
    show_activation_dialog()
else:
    verify_token_with_server()  # 매 실행마다 서버 재확인
    run_main_app()
```

---

## 4. 라이선스 키 포맷

### 포맷
```
NSP-XXXX-XXXX-XXXX
(대문자 + 숫자, 4자리씩 3그룹)
```

### 포맷 검사 (정규식)

```python
import re

def validate_key_format(key: str) -> bool:
    pattern = r'^[A-Z]{2,5}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
    return bool(re.match(pattern, key))
```

### 키 생성 (관리자 도구)

```python
import secrets, string

def generate_key(prefix="NSP") -> str:
    chars = string.ascii_uppercase + string.digits
    parts = [''.join(secrets.choice(chars) for _ in range(4)) for _ in range(3)]
    return f"{prefix}-{'-'.join(parts)}"

# 결과 예시: NSP-A3KX-9QWP-7ZTR
```

---

## 5. 서버 검증 (FastAPI)

### HWID 생성 — 클라이언트

```python
import uuid, hashlib, platform

def get_hwid() -> str:
    raw = f"{uuid.getnode()}{platform.node()}"  # MAC주소 + 컴퓨터명
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
```

### API 엔드포인트

```python
from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3, hmac, hashlib

app = FastAPI()

class ActivateRequest(BaseModel):
    key: str
    hwid: str

@app.post("/api/activate")
def activate(req: ActivateRequest):
    db = sqlite3.connect("licenses.db")
    row = db.execute(
        "SELECT used_hwid, max_devices FROM keys WHERE key=?",
        [req.key]
    ).fetchone()

    if not row:
        return {"ok": False, "reason": "invalid_key"}

    used_hwid, max_devices = row
    devices = used_hwid.split(",") if used_hwid else []

    if req.hwid not in devices:
        if len(devices) >= max_devices:
            return {"ok": False, "reason": "device_limit"}
        devices.append(req.hwid)
        db.execute("UPDATE keys SET used_hwid=? WHERE key=?",
                   [",".join(devices), req.key])
        db.commit()

    token = hmac.new(SECRET.encode(), f"{req.key}{req.hwid}".encode(),
                     hashlib.sha256).hexdigest()
    return {"ok": True, "token": token}
```

### DB 스키마

```sql
CREATE TABLE keys (
    key         TEXT PRIMARY KEY,
    plan        TEXT,           -- basic / pro / enterprise
    max_devices INTEGER DEFAULT 1,
    used_hwid   TEXT DEFAULT '',
    created_at  TEXT,
    expires_at  TEXT            -- NULL = 무기한
);
```

---

## 6. 보안 수준별 비교

| 방식 | 강도 | 크랙 난이도 | 오프라인 |
|------|------|-------------|---------|
| 로컬 검증만 | 매우 약함 | 5분 (조건문 패치) | 가능 |
| 서버 검증 (1회) | 중간 | exe 패치로 우회 | 불가 |
| **매 실행 서버 ping** | **강함** | **가짜 서버 구축 필요** | **불가** |
| 핵심 로직 서버 실행 | 매우 강함 | 실질적 불가 | 불가 |

**이 프로젝트 추천**: 매 실행 시 서버 토큰 재확인 방식.

### 보안 체크리스트
- [ ] HTTPS 필수 (HTTP는 키 평문 노출)
- [ ] Rate Limiting (초당 N회 초과 차단)
- [ ] 토큰에 만료 시간 포함 (JWT 또는 커스텀)
- [ ] 서버 시크릿 환경변수 관리 (하드코딩 금지)

---

## 7. 패키징 흐름

### 현재 프로젝트 상태
```
✅ Python 소스 (.py)     → remove_password_gui.py
✅ PyInstaller 빌드      → build.ps1 + pdf-unlock.spec
⬜ 라이선스 다이얼로그   → 미구현
⬜ 서버 연결             → 미구현
⬜ Inno Setup 인스톨러   → 미구현
```

### Inno Setup 스크립트 기본 구조

```ini
[Setup]
AppName=PDF Unlock
AppVersion=1.0
DefaultDirName={pf}\PDFUnlock
DefaultGroupName=PDF Unlock
OutputBaseFilename=pdf-unlock-setup

[Files]
Source: "dist\pdf-unlock.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\PDF Unlock"; Filename: "{app}\pdf-unlock.exe"

[Run]
; 설치 완료 후 자동 실행 (첫 실행 → 라이선스 창 표시)
Filename: "{app}\pdf-unlock.exe"; Flags: postinstall nowait
```

---

## 8. 서버 배포 옵션

| 서비스 | 난이도 | 비용 | 특징 |
|--------|--------|------|------|
| **Railway** | 쉬움 | 월 $5~ | Git push → 자동 배포 |
| Render | 쉬움 | 무료 티어 | 콜드 스타트 있음 |
| Supabase | 쉬움 | 무료 티어 | DB 포함, Edge Function |
| AWS Lambda | 중간 | 거의 무료 | 요청 수 적을 때 |

**1인 기업 초기 추천**: Railway + FastAPI + PostgreSQL

---

## 9. 구현 예상 시간

| 작업 | 예상 시간 |
|------|-----------|
| 라이선스 활성화 다이얼로그 (customtkinter) | 30분 |
| FastAPI 서버 + SQLite DB | 1시간 |
| 키 생성 관리 도구 | 20분 |
| Inno Setup 인스톨러 스크립트 | 30분 |
| Railway 배포 + HTTPS 설정 | 30분 |
| **합계** | **약 3시간** |
