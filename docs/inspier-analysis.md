# inspier 기술스택 분석

`C:\Program Files (x86)\inspier\_internal` 폴더 분석 결과.

---

## 기술스택 요약

| 역할 | 라이브러리 |
|------|-----------|
| **GUI 프레임워크** | PyQt5 |
| **UI 컴포넌트** | qfluentwidgets (PyQt Fluent Widgets 1.7.0) |
| **웹뷰** | PyQtWebEngine |
| **패키징** | PyInstaller (`_internal` 폴더 구조) |
| **코드 난독화 / 라이선스** | PyArmor (`pyarmor_runtime_000000`) |
| **AI** | Google Generative AI (Gemini), ONNX Runtime |
| **데이터 처리** | pandas, numpy, openpyxl |
| **PDF 처리** | pdfminer, pdfplumber, pymupdf (fitz) |
| **DB** | SQLite (`_sqlite3.pyd`) |
| **기타** | requests, cryptography, beautifulsoup4, scipy, torch, torchvision |

---

## UI 스타일 — qfluentwidgets

스크린샷의 사이드바 레이아웃, 카드 UI, Fluent Design 스타일이
모두 [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) 라이브러리에서 나온 것.

```python
pip install PyQt-Fluent-Widgets
```

Windows 11 Fluent Design 스타일을 PyQt5에서 바로 사용 가능.
Electron 없이 순수 Python으로 이 수준의 UI 구현 가능.

---

## 라이선스 보호 — PyArmor

서버 검증 방식이 아닌 **PyArmor** 자체 라이선스 시스템 사용.

```
pyarmor_runtime_000000/  ← PyArmor 런타임 (난독화된 코드 실행용)
```

- 소스코드를 바이트코드로 변환 + 암호화
- 라이선스 파일 없으면 실행 불가
- 역공학 난이도 높음

PyArmor 라이선스 방식:
```
pyarmor gen --bind-device ...   # HWID 바인딩
pyarmor gen --expired 2027-01-01  # 만료일 설정
```

---

## 패키징 구조

```
inspier/
├── inspier.exe          ← PyInstaller 진입점
├── _internal/           ← 모든 의존성 포함
│   ├── app/
│   │   └── resources/   ← 이미지, 아이콘 등 리소스
│   ├── pyarmor_runtime_000000/  ← 코드 보호 런타임
│   ├── PyQt5/           ← Qt 바이너리
│   ├── qfluentwidgets/  ← Fluent UI 컴포넌트
│   └── ...
├── unins000.exe         ← Inno Setup 언인스톨러
└── unins000.dat
```

Inno Setup으로 설치 파일 생성한 것 확인 (`unins000.exe` 존재).

---

## 참고 링크

- qfluentwidgets: https://github.com/zhiyiYo/PyQt-Fluent-Widgets
- PyArmor: https://pyarmor.readthedocs.io
