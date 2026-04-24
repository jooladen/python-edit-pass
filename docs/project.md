# PDF 비밀번호 제거 도구 — 프로젝트 메모

## 파일 구조

```
/
├── remove_password.py       # CLI 버전
├── remove_password_gui.py   # GUI 버전 (FreeSimpleGUI)
├── build.ps1                # exe 빌드 스크립트
├── dist/
│   └── pdf-unlock.exe       # 배포용 실행 파일 (고객 전달용)
└── docs/
```

---

## 실행 방법

### GUI (개발 중 테스트용)
```bash
python remove_password_gui.py
```

### CLI
```bash
# 비밀번호 아는 경우
python remove_password.py data/ --password 12345678

# 비밀번호 모르는 경우 (자동 탐색)
python remove_password.py data/ --brute-force
```

---

## 출력 파일
원본: `파일명.pdf` → 출력: `파일명_open.pdf` (같은 폴더)

---

## exe 빌드

### 빌드 환경
- 일반 Python 3.10.0은 PyInstaller/cx_Freeze 빌드 버그 있음
- **conda `pkg` 환경 (Python 3.10.11)** 으로 패키징해야 함

### 최초 환경 세팅 (1회만)
```bash
conda create -n pkg python=3.10.11 -y
conda run -n pkg pip install pikepdf FreeSimpleGUI pyinstaller
```

### 빌드 실행
`build.ps1` 우클릭 → **PowerShell로 실행**
또는:
```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```
→ `dist\pdf-unlock.exe` 생성

---

## 수정 시 작업 순서 (시간순)

코드나 빌드 설정 변경 후 반드시 이 순서대로 진행.

### 1단계 — 코드 수정
- `remove_password_gui.py` 수정 (GUI 로직/UI)
- `remove_password.py` 수정 (브루트포스 로직)

### 2단계 — Python에서 직접 실행 확인 (exe 없이)
```bash
python remove_password_gui.py
```
- GUI가 뜨고 파일 추가/실행이 정상 동작하는지 확인
- 문제 있으면 여기서 먼저 수정. exe 빌드 전에 반드시 통과해야 함.

### 3단계 — 기존 빌드 산출물 삭제
```powershell
Remove-Item -Recurse -Force dist, build, __pycache__, pdf-unlock.spec -ErrorAction SilentlyContinue
```
> 이전 캐시가 남아있으면 빌드가 변경사항을 반영 안 할 수 있음

### 4단계 — exe 빌드
`build.ps1` 우클릭 → PowerShell로 실행
- `dist\pdf-unlock.exe` 생성 확인

### 5단계 — exe 실행 테스트
더블클릭으로 직접 실행하여:
- GUI 화면이 정상적으로 뜨는지 확인
- 파일 추가 → 실행 동작 확인
- 에러 메시지 없는지 확인

---

## 핵심 트러블슈팅

### ★ Tcl 버전 충돌 오류 (완전 해결됨)
```
version conflict for package "Tcl": have 8.6.14, need exactly 8.6.15
```

**진짜 원인**: PyInstaller가 빌드 시 의존성을 자동 분석하는데,
`tcl86t.dll`을 pkg 환경(8.6.15)이 아닌 **base conda 환경(8.6.14)에서 가져옴**.
tcl 스크립트(init.tcl)는 pkg에서 가져와 8.6.15를 요구하는데, 로드되는 DLL은 8.6.14 → 충돌.

**해결 (두 가지 동시 적용)**:

1. `build.ps1`에 `--add-binary`로 pkg의 DLL을 명시적으로 번들 (base 버전 덮어씀):
```powershell
--add-binary "C:\Users\jooladen\anaconda3\envs\pkg\Library\bin\tcl86t.dll;."
--add-binary "C:\Users\jooladen\anaconda3\envs\pkg\Library\bin\tk86t.dll;."
```

2. `remove_password_gui.py` 최상단 frozen 블록에 `SetDllDirectoryW` 추가:
```python
import ctypes
if getattr(sys, 'frozen', False):
    _mp = sys._MEIPASS
    ctypes.windll.kernel32.SetDllDirectoryW(_mp)   # MEIPASS를 LoadLibrary 검색 1순위로
    os.environ['TCL_LIBRARY'] = os.path.join(_mp, 'tcl8.6')
    os.environ['TK_LIBRARY'] = os.path.join(_mp, 'tk8.6')
```
> `os.add_dll_directory()`, `os.environ['PATH']` 수정은 현재 프로세스의 LoadLibrary에 효과 없음.
> `ctypes.SetDllDirectoryW`만 표준 LoadLibrary 검색 경로에 실제로 영향을 줌.

### PyInstaller 빌드 실패 (IndexError: tuple index out of range)
**원인**: Python 3.10.0 bytecode 버그

**해결**: conda로 Python 3.10.11 환경 별도 생성 후 해당 환경에서 빌드

### 배치파일(.bat)에서 conda 미인식
**원인**: cmd에서 conda PATH 없음

**해결**: `.bat` 대신 `.ps1` 사용, pyinstaller 전체 경로 직접 지정:
```
C:\Users\jooladen\anaconda3\envs\pkg\Scripts\pyinstaller.exe
```

---

## 의존성

| 패키지 | 용도 |
|---|---|
| pikepdf | PDF 비밀번호 제거 핵심 |
| FreeSimpleGUI | GUI (PySimpleGUI 무료 포크) |
| pyinstaller | exe 패키징 (pkg 환경에서만) |

---

## GUI 주요 동작
- 기본: "모름 (자동 탐색)" 체크된 상태로 시작
- 체크 해제 시 비밀번호 입력창 활성화 + 포커스 이동
- 파일 다이얼로그: tkinter filedialog 직접 사용 (FreeSimpleGUI popup은 Windows에서 불안정)
- `_open.pdf` 파일은 목록 추가 차단 (이미 처리된 파일)
