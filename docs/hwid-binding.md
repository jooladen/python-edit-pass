❯ sqllite만 뚫으면 다 뚫리겠네?

● 아니요, SQLite는 앱 데이터(고객 정보, 캘린더 등) 저장용이고 라이선스 보호는 별개입니다.

  inspier의 실제 보호 구조:

  SQLite DB          → 고객/영업 데이터 저장 (뚫어도 코드 실행 불가)
  PyArmor 런타임     → 코드 자체가 암호화됨
                       라이선스 없으면 pyarmor_runtime이 실행 거부

  PyArmor는 소스코드를 암호화된 바이트코드로 변환해서 배포합니다. SQLite를 열어도 실행 파일 자체가 PyArmor 라이선스    
  검증을 통과해야 돌아가는 구조입니다.

  크랙하려면 PyArmor 런타임 자체를 우회해야 하는데, 이게 SQLite보다 훨씬 어렵습니다.

❯ 우회는 어케 함?

● 그건 설명 못 드립니다.

  타인이 만든 상용 소프트웨어 크랙은 저작권법 위반입니다.

  궁금하신 게 "내 프로그램을 PyArmor로 어떻게 보호하나"라면 설명드릴 수 있습니다.

❯ 나 정보보안기사야...누가 내꺼 뚫음 어케함? 방어를 해야지..어디를 방어해야되?

● 정보보안 관점에서 설명합니다.

  ---
  PyArmor 주요 공격 벡터

  ┌────────────────────┬────────────────────────────────────────────┐
  │     공격 방식      │                    원리                    │
  ├────────────────────┼────────────────────────────────────────────┤
  │ 메모리 덤프        │ 실행 중 복호화된 바이트코드를 RAM에서 추출 │
  ├────────────────────┼────────────────────────────────────────────┤
  │ 런타임 후킹        │ pyarmor_runtime DLL 함수 가로채기          │
  ├────────────────────┼────────────────────────────────────────────┤
  │ 라이선스 파일 복제 │ license.lic를 다른 PC에 복사               │
  ├────────────────────┼────────────────────────────────────────────┤
  │ 디버거 attach      │ 실행 중 중단점으로 검증 로직 추적          │
  └────────────────────┴────────────────────────────────────────────┘

  ---
  방어 포인트

  1. 안티디버깅
  import ctypes
  if ctypes.windll.kernel32.IsDebuggerPresent():
      sys.exit()

  2. HWID 바인딩 강화
  - PyArmor --bind-device 옵션으로 특정 PC에만 실행 허용
  - MAC주소 + CPU ID + 디스크 시리얼 조합

  3. 핵심 로직 서버 이전 (가장 강력)
  - 크랙해도 서버 없이는 핵심 기능 동작 안 함

  4. 주기적 온라인 재검증
  - 실행 시마다 서버 ping — 라이선스 취소 즉시 적용 가능

  5. PyArmor + 추가 난독화 중첩
  - PyArmor 위에 별도 코드 난독화 레이어 추가

  ---
  현실적 결론: 메모리 덤프는 막기 어렵습니다. 그래서 핵심 비즈니스 로직을 서버에 두는 게 가장 확실한 방어선입니다. 

  ----------------------------------------------------

# HWID 바인딩 — 라이선스 키 공유 방지

## 왜 필요한가

HWID 바인딩이 없으면 라이선스 키 하나를 여러 PC에서 공유해도
서버가 막을 방법이 없다. 키 포맷 검증만으로는 불충분하다.

---

## 1. 클라이언트 — HWID 생성

```python
import uuid, hashlib, platform, subprocess

def get_hwid() -> str:
    mac = str(uuid.getnode())          # MAC 주소
    hostname = platform.node()         # 컴퓨터명
    try:
        serial = subprocess.check_output(
            "wmic diskdrive get serialnumber", shell=True
        ).decode().split("\n")[1].strip()  # 디스크 시리얼 (Windows)
    except:
        serial = ""

    raw = f"{mac}{hostname}{serial}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]
```

---

## 2. 서버 — 활성화 시 HWID 등록

```python
@app.post("/api/activate")
def activate(req: ActivateRequest):
    row = db.execute(
        "SELECT hwid, max_devices FROM keys WHERE key=?",
        [req.key]
    ).fetchone()

    if not row:
        return {"ok": False, "reason": "invalid_key"}

    registered_hwids = row["hwid"].split(",") if row["hwid"] else []

    # 이미 등록된 기기면 통과
    if req.hwid in registered_hwids:
        return {"ok": True}

    # 기기 수 초과 → 거부
    if len(registered_hwids) >= row["max_devices"]:
        return {"ok": False, "reason": "다른 PC에서 이미 활성화된 키입니다"}

    # 새 HWID 등록
    registered_hwids.append(req.hwid)
    db.execute("UPDATE keys SET hwid=? WHERE key=?",
               [",".join(registered_hwids), req.key])
    db.commit()
    return {"ok": True}
```

---

## 3. 서버 — 매 실행 시 HWID 재확인

활성화 1회로 끝내면 키를 복사해도 막기 어렵다.
실행할 때마다 서버에서 HWID를 재확인해야 한다.

```python
@app.post("/api/verify")
def verify(req: VerifyRequest):
    row = db.execute(
        "SELECT hwid FROM keys WHERE key=?",
        [req.key]
    ).fetchone()

    if not row:
        return {"ok": False, "reason": "invalid_key"}

    registered = row["hwid"].split(",") if row["hwid"] else []

    if req.hwid not in registered:
        return {"ok": False, "reason": "등록되지 않은 기기"}

    return {"ok": True}
```

---

## 4. DB 스키마

```sql
CREATE TABLE keys (
    key         TEXT PRIMARY KEY,
    hwid        TEXT DEFAULT '',      -- 등록된 HWID (콤마 구분)
    max_devices INTEGER DEFAULT 1,    -- 허용 기기 수
    plan        TEXT,
    created_at  TEXT,
    expires_at  TEXT
);
```

---

## 5. 클라이언트 실행 흐름

```
앱 실행
  ↓
license.dat 존재?
  ├─ NO  → 활성화 창 표시 → POST /api/activate (key + hwid)
  └─ YES → POST /api/verify (key + hwid)
              ├─ ok: true  → 메인 앱 실행
              └─ ok: false → "등록되지 않은 기기" 메시지 + 종료
```

---

## 취약점 비교

| 방식 | 키 공유 가능? | 비고 |
|------|-------------|------|
| 키 포맷만 검증 | 가능 (무제한) | inspier 사례 |
| 서버 검증 (HWID 없음) | 가능 | 키만 맞으면 통과 |
| **서버 검증 + HWID 바인딩** | **불가** | **권장 방식** |
| 매 실행 HWID 재확인 | 불가 + 즉시 차단 가능 | 가장 강력 |
