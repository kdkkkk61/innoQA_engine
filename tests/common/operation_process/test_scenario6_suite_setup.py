"""운용 프로세스 — 시나리오 6: 연계 데이터 준비 (날짜본 전환 2026-07-03).

sc6 = 다음 테스트(태그 sc6)가 참조할 데이터를 만들어 '삭제하지 않고 남긴다'(표준 정의).
명명: '[AUTO]'(날짜 없음)=휘발성→sc5d 가 삭제 / '[AUTO_<MMDD>]'(날짜본)=영속·연계→run 내 보존
  (startswith('[AUTO]') 가 '[AUTO_'는 불일치 → sc5d 자동 제외).
날짜본·레거시 KEEP 은 다음 run 의 시작 clean slate 가 전부 삭제(오늘 것 포함 — 사용자 결정 2026-07-03:
  태그 등록 상태면 참조 잠금 차단이 뜨는데 그 동작 자체도 테스트 범위, 차단 시 DELME rename) 후 sc6 재생성.
소비자: 태그 sc6 — 오늘 날짜본 우선, 레거시 KEEP fallback (태그 재구성 전까지 이중 지원).
"""
import time

from pages.npouch_operation_process_page import NpouchOperationProcessPage
from tests.common.operation_process._base import OperationProcessBase


class TestOperationProcessScenario6SuiteSetup(OperationProcessBase):
    """운용 프로세스 — 시나리오 6: 연계 데이터 준비."""

    def _new_page(self, logged_in_page, settings):
        page = NpouchOperationProcessPage(logged_in_page, settings)
        self._page = page.page
        return page

    def test_scenario6a_dated_handoff(self, logged_in_page, settings):
        print("\n━━ [운용 프로세스] sc6a: 연계 날짜본 준비 ━━━")
        p = self._new_page(logged_in_page, settings)
        p.navigate_to()
        dated = f"[AUTO_{time.strftime('%m%d')}]_cm_proc"          # 예: [AUTO_0703]_cm_proc
        # '[AUTO' 필터가 날짜본도 prefix 매칭 — 잔존 확인(같은 날 재실행 재사용)
        p.ensure_auto_filter()
        already = dated in p.get_item_names()
        p._restore_page_size()
        if already:
            self._add("pass", "sc6a — 연계 날짜본 잔존 재사용",
                      f"입력: {dated!r} 이미 존재(같은 날 재실행) / 결과: 날짜본 재사용", sc=6)
        else:
            p.add_item(dated)
            p.ensure_auto_filter()
            exists = dated in p.get_item_names()
            self._add("pass" if exists else "fail", "sc6a — 연계 날짜본 생성",
                      f"입력: {dated!r} 생성 / 결과: {'목록에 존재' if exists else '없음'}", sc=6,
                      repro=f"1. {dated} 추가\n2. 목록 존재 확인\n3. 삭제하지 않고 종료")
        # 삭제하지 않고 종료 — 태그 관리 sc6 에서 태그에 등록해 cross-page 연계 검증
        self._add("skip", "sc6a — 연계 데이터 남겨두기(삭제 안 함)",
                  f"{dated!r} — 태그 관리(시나리오 6)에서 태그에 등록 예정. "
                  "휘발성 [AUTO] 정리는 sc5d, 이전 날짜본 정리는 다음 run 의 시작 cleanup 담당.", sc=6,
                  screenshot=False)
