"""
utils/scan_logger.py — UIScanner 단계별 디버그 로거

reports/scan_debug.log 에 스캔 진행 상황을 기록한다.
- 각 패턴 스캔 시작/완료 로그
- Playwright 액션 직전 로그 (어느 동작에서 에러가 났는지 추적)
- 에러 발생 시 full traceback 기록

사용법:
    from utils.scan_logger import make_scan_logger
    log = make_scan_logger()
    log.debug("[plain_checkbox] input#foo → 라벨 클릭 시도")
"""

import logging
from pathlib import Path


def make_scan_logger(log_dir: str = "reports") -> logging.Logger:
    """
    scan_debug.log 파일 핸들러가 붙은 Logger를 반환한다.

    - 매 테스트 실행마다 로그 파일을 덮어씀 (mode="w")
    - 이미 핸들러가 등록된 경우 재사용 (중복 로그 방지)
    """
    logger = logging.getLogger("ui_scanner")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    fh = logging.FileHandler(
        Path(log_dir) / "scan_debug.log",
        encoding="utf-8",
        mode="w",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(fh)
    return logger
