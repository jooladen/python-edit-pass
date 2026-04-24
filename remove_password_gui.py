import os
import sys

if getattr(sys, 'frozen', False):
    import ctypes
    _mp = sys._MEIPASS
    # PyInstaller가 base conda의 tcl86t.dll(8.6.14)을 번들함.
    # --add-binary로 pkg의 8.6.15를 덮어쓰고, SetDllDirectoryW로
    # MEIPASS를 LoadLibrary 표준 검색 경로에 삽입해 올바른 버전이 로드되도록 함.
    ctypes.windll.kernel32.SetDllDirectoryW(_mp)
    os.environ['TCL_LIBRARY'] = os.path.join(_mp, 'tcl8.6')
    os.environ['TK_LIBRARY'] = os.path.join(_mp, 'tk8.6')

import threading
import calendar
from pathlib import Path
from tkinter import filedialog, Tk

import FreeSimpleGUI as sg
import pikepdf


# ── 핵심 로직 ──────────────────────────────────────────────

def make_output_path(src: Path) -> Path:
    return src.parent / (src.stem + "_open" + src.suffix)


def remove_one(src: Path, password: str) -> tuple[bool, str]:
    dst = make_output_path(src)
    try:
        with pikepdf.open(src, password=password) as pdf:
            pdf.save(dst, linearize=False,
                     object_stream_mode=pikepdf.ObjectStreamMode.preserve)
        dst_kb = dst.stat().st_size / 1024
        return True, f"[OK]  {src.name}  ->  {dst_kb:.0f}KB"
    except pikepdf.PasswordError:
        return False, f"[NG]  {src.name}  --  비밀번호 오류"
    except Exception as e:
        return False, f"[NG]  {src.name}  --  {e}"


def brute_force_smart(src: Path, progress_cb=None) -> tuple[bool, str]:
    import time
    dst = make_output_path(src)
    start = time.time()
    count = 0
    for year in range(1940, 2011):
        for month in range(1, 13):
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                pw = f"{year:04d}{month:02d}{day:02d}"
                count += 1
                if progress_cb:
                    progress_cb(f"날짜 탐색 중... {pw}")
                try:
                    with pikepdf.open(src, password=pw) as pdf:
                        pdf.save(dst, linearize=False,
                                 object_stream_mode=pikepdf.ObjectStreamMode.preserve)
                    elapsed = time.time() - start
                    return True, f"[OK]  {src.name}  비밀번호:{pw}  ({elapsed:.1f}초, {count}회)"
                except pikepdf.PasswordError:
                    continue
                except Exception as e:
                    return False, f"[NG]  {src.name}  --  {e}"
    for i in range(100_000_000):
        pw = f"{i:08d}"
        count += 1
        if progress_cb and i % 10_000 == 0:
            progress_cb(f"전체 탐색 중... {pw}")
        try:
            with pikepdf.open(src, password=pw) as pdf:
                pdf.save(dst, linearize=False,
                         object_stream_mode=pikepdf.ObjectStreamMode.preserve)
            elapsed = time.time() - start
            return True, f"[OK]  {src.name}  비밀번호:{pw}  ({elapsed:.1f}초)"
        except pikepdf.PasswordError:
            continue
        except Exception as e:
            return False, f"[NG]  {src.name}  --  {e}"
    return False, f"[NG]  {src.name}  --  비밀번호를 찾지 못했습니다"


# ── 레이아웃 ───────────────────────────────────────────────

sg.theme("LightBlue2")
FONT      = ("Malgun Gothic", 10)
FONT_BOLD = ("Malgun Gothic", 10, "bold")
FONT_MONO = ("Consolas", 9)
FONT_HINT = ("Malgun Gothic", 9, "italic")
BG        = "#e8f4f8"   # 연한 하늘색 배경
BTN_MAIN  = ("white", "#5b9bd5")   # 파스텔 블루 버튼
BTN_RUN   = ("white", "#4a86c8")

layout = [
    # ── 파일 추가/삭제 ──
    [
        sg.Button("파일 추가", key="-ADD_FILES-", size=(10, 1), button_color=BTN_MAIN),
        sg.Button("폴더 선택", key="-ADD_FOLDER-", size=(10, 1), button_color=BTN_MAIN),
        sg.Push(),
        sg.Button("선택 삭제", key="-DEL_SEL-", size=(10, 1)),
        sg.Button("목록 초기화", key="-CLEAR_LIST-", size=(10, 1)),
    ],
    # ── 파일 목록 ──
    [
        sg.Listbox(
            values=[], key="-FILELIST-", size=(72, 7),
            select_mode=sg.LISTBOX_SELECT_MODE_EXTENDED,
            font=FONT_MONO, expand_x=True,
            highlight_background_color="#5b9bd5",
            highlight_text_color="white",
        )
    ],
    [sg.HorizontalSeparator(pad=(0, 6))],
    # ── 비밀번호 ──
    [
        sg.Text("비밀번호", size=(8, 1)),
        sg.Input(key="-PW-", size=(20, 1), password_char="*", disabled=True),
        sg.Checkbox("암호 보임", key="-SHOW_PW-", enable_events=True),
        sg.Push(),
        sg.Checkbox("모름 (자동 탐색)", key="-BRUTE-", default=True, enable_events=True),
    ],
    [
        sg.Text("", size=(8, 1)),
        sg.Text("* 체크 해제 시 암호 직접 입력 모드 전환  |  암호 아는 경우 훨씬 빠름  |  모를 경우 개당 10초 내외",
                font=FONT_HINT, text_color="#888888", expand_x=True),
    ],
    [sg.HorizontalSeparator(pad=(0, 6))],
    # ── 실행 ──
    [sg.Button("실  행", key="-RUN-", expand_x=True, size=(20, 2),
               font=FONT_BOLD, button_color=BTN_RUN)],
    # ── 진행 ──
    [sg.ProgressBar(100, key="-PROG-", size=(10, 18), expand_x=True, bar_color=("#5b9bd5", "#dde8f0"))],
    [sg.Text("", key="-STATUS-", font=("Malgun Gothic", 9), text_color="#555555", expand_x=True)],
    [sg.HorizontalSeparator(pad=(0, 6))],
    # ── 결과 ──
    [
        sg.Text("결과"),
        sg.Push(),
        sg.Button("결과 초기화", key="-CLEAR_LOG-", size=(10, 1)),
    ],
    [
        sg.Multiline(
            key="-LOG-", size=(72, 6), disabled=True,
            font=FONT_MONO, background_color="#f0f7fb",
            expand_x=True, autoscroll=True,
        )
    ],
]


# ── 이벤트 루프 ────────────────────────────────────────────

def run_app():
    window = sg.Window("PDF 비밀번호 제거", layout, font=FONT,
                       size=(640, 540), finalize=True)
    window["-FILELIST-"].Widget.config(activestyle="none")

    files: list[Path] = []

    def refresh_list():
        window["-FILELIST-"].update(
            [f"  {f.name}   ({f.stat().st_size / 1024:.0f}KB)" for f in files]
        )

    def log(text: str, color: str = "black"):
        window["-LOG-"].update(disabled=False)
        window["-LOG-"].print(text, text_color=color)
        window["-LOG-"].update(disabled=True)

    def process_thread(file_list, password, brute):
        total = len(file_list)
        ok = ng = 0
        for i, f in enumerate(file_list, 1):
            window["-STATUS-"].update(f"{i}/{total}  처리 중: {f.name}")
            if brute:
                cb = lambda msg: window["-STATUS-"].update(msg)
                success, msg = brute_force_smart(f, progress_cb=cb)
            else:
                success, msg = remove_one(f, password)
            color = "#16a34a" if success else "#dc2626"
            log(msg, color)
            window["-PROG-"].update(current_count=int(i / total * 100))
            if success:
                ok += 1
            else:
                ng += 1
        window["-STATUS-"].update(
            f"완료: {ok}개 성공" + (f", {ng}개 실패" if ng else ""))
        window["-RUN-"].update(disabled=False)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break

        elif event == "-ADD_FILES-":
            root = Tk(); root.withdraw(); root.attributes("-topmost", True)
            paths = filedialog.askopenfilenames(
                parent=root, filetypes=[("PDF", "*.pdf")])
            root.destroy()
            skipped = []
            for p in paths:
                path = Path(p)
                if path.stem.endswith("_open"):
                    skipped.append(path.name)
                elif path not in files:
                    files.append(path)
            refresh_list()
            if skipped:
                sg.popup_ok("이미 처리된 파일은 추가되지 않습니다:\n" + "\n".join(skipped),
                            title="건너뜀")

        elif event == "-ADD_FOLDER-":
            root = Tk(); root.withdraw(); root.attributes("-topmost", True)
            folder = filedialog.askdirectory(parent=root)
            root.destroy()
            if folder:
                for path in sorted(Path(folder).glob("*.pdf")):
                    if not path.stem.endswith("_open") and path not in files:
                        files.append(path)
                refresh_list()

        elif event == "-DEL_SEL-":
            sel = values["-FILELIST-"]
            files = [f for f in files if
                     f"  {f.name}   ({f.stat().st_size / 1024:.0f}KB)" not in sel]
            refresh_list()

        elif event == "-CLEAR_LIST-":
            files.clear()
            refresh_list()

        elif event == "-SHOW_PW-":
            window["-PW-"].update(password_char="" if values["-SHOW_PW-"] else "*")

        elif event == "-BRUTE-":
            window["-PW-"].update(disabled=values["-BRUTE-"])
            if not values["-BRUTE-"]:
                window["-PW-"].set_focus()

        elif event == "-CLEAR_LOG-":
            window["-LOG-"].update("", disabled=True)
            window["-PROG-"].update(current_count=0)
            window["-STATUS-"].update("")

        elif event == "-RUN-":
            if not files:
                sg.popup_ok("파일을 먼저 추가하세요.", title="알림")
                continue
            brute = values["-BRUTE-"]
            password = values["-PW-"].strip()
            if not brute and not password:
                sg.popup_ok("비밀번호를 입력하거나 '모름 (자동 탐색)'을 선택하세요.", title="알림")
                continue
            window["-RUN-"].update(disabled=True)
            window["-PROG-"].update(current_count=0)
            window["-LOG-"].update("", disabled=True)
            threading.Thread(
                target=process_thread,
                args=(list(files), password, brute),
                daemon=True,
            ).start()

    window.close()


if __name__ == "__main__":
    run_app()
