# Design: PDF 비밀번호 제거 도구

## 목적

숫자 8자리 비밀번호로 잠긴 PDF 파일에서 비밀번호를 제거하고,
원본 파일을 보존하면서 암호 없는 사본을 생성한다.

---

## 요구사항

| 항목 | 내용 |
|---|---|
| 입력 | 비밀번호 잠긴 PDF 파일 (단일 또는 폴더 전체) |
| 비밀번호 형식 | 숫자 8자리 (`00000000` ~ `99999999`) |
| 출력 | 비밀번호 없는 PDF (`원본파일명_open.pdf`) |
| 원본 보존 | 원본 파일 절대 수정 금지 |
| 파일 크기 | 원본 대비 ±5% 이내 유지 |
| 배치 처리 | 폴더 내 PDF 전체 일괄 처리 |

---

## 출력 파일명 규칙

```
원본: 개인진료정보내역(기본진료정보)_20260413.pdf
출력: 개인진료정보내역(기본진료정보)_20260413_open.pdf
```

원본과 동일한 폴더에 나란히 생성.

---

## 기술 스택

- **Python 3.x** (conda `pkg` 환경 3.10.11 권장 — exe 빌드 시)
- **pikepdf** — PDF 비밀번호 제거 핵심 라이브러리 (QPDF 기반)
- **FreeSimpleGUI** — GUI 버전 (PySimpleGUI 무료 포크)
- **PyInstaller** — exe 단일 파일 패키징 (고객 배포용)

### pikepdf를 선택한 이유

| 라이브러리 | 파일 크기 보존 | 권한 암호 제거 | 안정성 |
|---|---|---|---|
| pikepdf | ✅ 스트림 보존 옵션 | ✅ | ✅ 높음 |
| PyMuPDF | ❌ 재렌더링 | ✅ | ✅ 높음 |
| PyPDF2 | ❌ 재압축 | ❌ 불안정 | ❌ 낮음 |

---

## 처리 흐름

```
입력 (파일 또는 폴더)
    │
    ▼
비밀번호 입력 (--password) 또는 브루트포스 (--brute-force)
    │
    ▼
pikepdf.open(src, password=pw)
    │
    ├─ 성공 → pdf.save(dst, object_stream_mode=preserve)
    │              → 출력: 원본명_open.pdf
    │
    └─ 실패 → 에러 로그 출력 후 다음 파일로 이동
```

---

## CLI 인터페이스

```bash
# 단일 파일, 비밀번호 지정
python remove_password.py data/파일.pdf --password 12345678

# 폴더 전체 배치, 비밀번호 지정
python remove_password.py data/ --password 12345678

# 비밀번호 모를 때 브루트포스
python remove_password.py data/ --brute-force

# 출력 경로 지정 (기본: 원본과 동일 폴더)
python remove_password.py data/ --password 12345678 --output out/
```

---

## 파일 크기 보존 전략

```python
pdf.save(
    output_path,
    linearize=False,                                         # 선형화 비활성 (크기 증가 방지)
    object_stream_mode=pikepdf.ObjectStreamMode.preserve     # 원본 스트림 그대로 유지
)
```

---

## 모듈 구조 (`remove_password.py`)

| 함수 | 역할 |
|---|---|
| `remove_password(src, password, dst)` | 단일 파일 비밀번호 제거 |
| `batch_remove(folder, password, output_dir, brute=False)` | 폴더 내 PDF 전체 처리 |
| `brute_force_smart(src, dst)` | 날짜 패턴(YYYYMMDD) 우선 시도 → 실패 시 전체 순회로 전환 |
| `brute_force_8digit(src, dst)` | 00000000~99999999 멀티프로세스 순회 |
| `make_output_path(src, output_dir=None)` | 출력 경로 생성 (`_open` 접미사) |
| `main()` | CLI 진입점 |

---

## 테스트 계획

1. **단일 파일 테스트** — 가장 작은 파일(217KB)로 우선 검증
2. **파일 크기 확인** — 원본 vs 출력 크기 비교 출력
3. **배치 처리 테스트** — data/ 폴더 전체 3개 파일 처리
4. **원본 무결성 확인** — 원본 파일 크기/수정일 변화 없어야 함
