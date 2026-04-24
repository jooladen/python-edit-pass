"""
PDF 비밀번호 제거 도구
사용법: python remove_password.py <파일 또는 폴더> --password <숫자8자리>
"""
import argparse
import os
import sys
from pathlib import Path

try:
    import pikepdf
except ImportError:
    print("[오류] pikepdf가 설치되지 않았습니다. 설치 중...")
    os.system(f"{sys.executable} -m pip install pikepdf")
    import pikepdf


def make_output_path(src: Path, output_dir: Path | None = None) -> Path:
    stem = src.stem + "_open"
    name = stem + src.suffix
    base = output_dir if output_dir else src.parent
    return base / name


def remove_password(src: Path, password: str, dst: Path | None = None) -> tuple[bool, str]:
    dst = dst or make_output_path(src)
    try:
        with pikepdf.open(src, password=password) as pdf:
            pdf.save(
                dst,
                linearize=False,
                object_stream_mode=pikepdf.ObjectStreamMode.preserve,
            )
        src_kb = src.stat().st_size / 1024
        dst_kb = dst.stat().st_size / 1024
        ratio = dst_kb / src_kb * 100
        return True, f"완료 | 원본 {src_kb:.1f}KB → 출력 {dst_kb:.1f}KB ({ratio:.1f}%) | {dst.name}"
    except pikepdf.PasswordError:
        return False, f"비밀번호 오류: {src.name}"
    except Exception as e:
        return False, f"처리 실패 ({src.name}): {e}"


def _generate_date_passwords(year_start: int = 1940, year_end: int = 2010):
    """YYYYMMDD 형식 날짜 조합 생성"""
    import itertools
    for year in range(year_start, year_end + 1):
        for month in range(1, 13):
            import calendar
            days = calendar.monthrange(year, month)[1]
            for day in range(1, days + 1):
                yield f"{year:04d}{month:02d}{day:02d}"


def brute_force_smart(src: Path, dst: Path | None = None) -> tuple[bool, str]:
    """날짜 패턴(YYYYMMDD) 우선 시도 — 건강보험공단 문서에 효과적"""
    import time

    dst = dst or make_output_path(src)
    print(f"스마트 브루트포스: {src.name}")
    print(f"  1단계: 날짜 패턴(YYYYMMDD, 1940~2010) 시도 중...")

    start = time.time()
    count = 0
    for pw in _generate_date_passwords():
        try:
            with pikepdf.open(src, password=pw) as pdf:
                pdf.save(dst, linearize=False,
                         object_stream_mode=pikepdf.ObjectStreamMode.preserve)
            elapsed = time.time() - start
            return True, f"비밀번호: {pw} | {elapsed:.1f}초 ({count}번 시도) | 저장: {dst.name}"
        except pikepdf.PasswordError:
            count += 1
        except Exception as e:
            return False, f"처리 실패: {e}"

    elapsed = time.time() - start
    print(f"  날짜 패턴 실패 ({count}개, {elapsed:.1f}초) → 전체 브루트포스로 전환...")
    return brute_force_8digit(src, dst)


def _try_range(args: tuple) -> str | None:
    """워커 프로세스: start~end 범위 시도, 찾으면 비밀번호 반환"""
    src_str, start, end, found_flag = args
    src = Path(src_str)
    for i in range(start, end):
        if found_flag.value:
            return None
        pw = f"{i:08d}"
        try:
            with pikepdf.open(src, password=pw):
                pass
            return pw
        except pikepdf.PasswordError:
            continue
        except Exception:
            continue
    return None


def brute_force_8digit(src: Path, dst: Path | None = None) -> tuple[bool, str]:
    import multiprocessing
    import time

    dst = dst or make_output_path(src)
    total = 100_000_000
    cpu = min(multiprocessing.cpu_count(), 8)
    chunk = total // cpu

    print(f"브루트포스 시작: {src.name}")
    print(f"  CPU {cpu}개 병렬 | 범위: 00000000 ~ 99999999")

    manager = multiprocessing.Manager()
    found_flag = manager.Value("b", False)

    ranges = [
        (str(src), i * chunk, min((i + 1) * chunk, total), found_flag)
        for i in range(cpu)
    ]

    start_time = time.time()
    found_pw = None

    with multiprocessing.Pool(processes=cpu) as pool:
        for result in pool.imap_unordered(_try_range, ranges, chunksize=1):
            if result is not None:
                found_pw = result
                found_flag.value = True
                pool.terminate()
                break

    elapsed = time.time() - start_time

    if found_pw:
        with pikepdf.open(src, password=found_pw) as pdf:
            pdf.save(
                dst,
                linearize=False,
                object_stream_mode=pikepdf.ObjectStreamMode.preserve,
            )
        return True, f"비밀번호: {found_pw} | {elapsed:.1f}초 소요 | 저장: {dst.name}"

    return False, f"비밀번호를 찾지 못했습니다 ({elapsed:.1f}초 소요)"


def batch_remove(
    folder: Path,
    password: str | None,
    output_dir: Path | None = None,
    brute: bool = False,
) -> None:
    pdfs = sorted(
        [p for p in folder.glob("*.pdf") if not p.stem.endswith("_open")],
        key=lambda p: p.stat().st_size,
    )
    if not pdfs:
        print("처리할 PDF 파일이 없습니다.")
        return

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    print(f"총 {len(pdfs)}개 파일 처리 시작 (크기 오름차순)\n")
    ok = 0
    fail = 0
    for pdf in pdfs:
        dst = make_output_path(pdf, output_dir)
        if brute:
            success, msg = brute_force_smart(pdf, dst)
        else:
            success, msg = remove_password(pdf, password, dst)

        status = "OK" if success else "NG"
        print(f"  [{status}] {msg}")
        if success:
            ok += 1
        else:
            fail += 1

    print(f"\n완료: {ok}개 성공, {fail}개 실패")


def main() -> None:
    parser = argparse.ArgumentParser(description="PDF 비밀번호 제거 도구")
    parser.add_argument("target", help="PDF 파일 또는 폴더 경로")
    parser.add_argument("--password", "-p", help="숫자 8자리 비밀번호")
    parser.add_argument("--brute-force", action="store_true", help="비밀번호 브루트포스 탐색")
    parser.add_argument("--output", "-o", help="출력 폴더 경로 (기본: 원본과 동일)")
    args = parser.parse_args()

    target = Path(args.target)
    output_dir = Path(args.output) if args.output else None

    if not target.exists():
        print(f"[오류] 경로를 찾을 수 없습니다: {target}")
        sys.exit(1)

    if not args.password and not args.brute_force:
        print("[오류] --password 또는 --brute-force 중 하나를 지정하세요.")
        sys.exit(1)

    if target.is_file():
        dst = make_output_path(target, output_dir)
        if args.brute_force:
            success, msg = brute_force_smart(target, dst)
        else:
            success, msg = remove_password(target, args.password, dst)
        status = "OK" if success else "NG"
        print(f"[{status}] {msg}")
    else:
        batch_remove(target, args.password, output_dir, brute=args.brute_force)


if __name__ == "__main__":
    main()
