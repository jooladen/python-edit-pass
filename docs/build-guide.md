# 다른 PC에서 빌드하기

## 전제 조건

- Windows PC
- Anaconda 설치 (또는 Python 3.11+)
- Git 설치

---

## 1단계: 저장소 클론

```powershell
git clone <저장소 URL>
cd python-edit-pass
```

---

## 2단계: Python 환경 설치

```powershell
conda create -n pkg python=3.11
conda activate pkg
```

---

## 3단계: 패키지 설치

```powershell
pip install -r requirements.txt
```

> **참고**: `requirements.txt`가 없으면 원래 PC에서 먼저 생성
> ```powershell
> conda activate pkg
> pip freeze > requirements.txt
> ```

---

## 4단계: Tcl/Tk 경로 확인 및 build.ps1 수정

다른 PC에서 Tcl/Tk 경로는 다를 수 있습니다. 아래 명령어로 확인:

```powershell
python -c "import tkinter; print(tkinter.__file__)"
```

출력 예시:
```
C:\Users\홍길동\anaconda3\envs\pkg\lib\tkinter\__init__.py
```

이 경로 기준으로 `build.ps1` 상단 4개 변수를 수정:

```powershell
$pyinstaller = "C:\Users\홍길동\anaconda3\envs\pkg\Scripts\pyinstaller.exe"
$tcl    = "C:\Users\홍길동\anaconda3\envs\pkg\Library\lib\tcl8.6"
$tk     = "C:\Users\홍길동\anaconda3\envs\pkg\Library\lib\tk8.6"
$tclDll = "C:\Users\홍길동\anaconda3\envs\pkg\Library\bin\tcl86t.dll"
$tkDll  = "C:\Users\홍길동\anaconda3\envs\pkg\Library\bin\tk86t.dll"
```

---

## 5단계: 빌드 실행

```powershell
.\build.ps1
```

성공 시 `dist\pdf-unlock.exe` 생성 완료.

---

## 자주 발생하는 에러

| 에러 메시지 | 원인 | 해결 |
|-------------|------|------|
| `Can't find a usable init.tcl` | Tcl/Tk 경로 잘못됨 | 4단계 경로 재확인 |
| `pyinstaller: command not found` | pyinstaller 미설치 | `pip install pyinstaller` |
| `ModuleNotFoundError: pikepdf` | requirements 누락 | `pip install -r requirements.txt` |
