"""시큐어존 정책 — 시나리오 0: 신규/제거 UI 자동 감지 (diff-only).

접근제어 sc0 와 목적 동일(회귀 감지)이나, 정책 모달은
  ① 기본반출정책(isSzAgentPolicyTypeTakeoutDefault) = 전역 singleton, 클릭 시 데이터 위험
  ② 중첩 gating + disabled 종속 체크박스
때문에 UIScanner 의 필드 클릭형 자동검증을 쓰지 않는다.
대신 core.scan_diff 로 yaml baseline ↔ 모달 DOM 을 '비교만' 한다 (요소 인터랙션 0).

감지:
  - DOM 에만 존재  → 🆕 신규 요소 (warn)  : 제품 UI 추가 (yaml baseline 갱신 필요)
  - yaml 에만 존재 → ❌ 제거 요소 (warn)  : 회귀 후보 (요소 사라짐)
  - 둘 다 존재     → 정상 (sc2~4 에서 개별 동작 검증)
"""
import yaml as _yaml
from pathlib import Path

from core.scan_diff import (
    extract_yaml_selectors, extract_dom_selectors, compare,
    extract_yaml_labels, extract_dom_labels, extract_dom_attributes,
    extract_dom_hidden,
)
from pages.secure_zone_agent_policy_page import SecureZoneAgentPolicyPage
from tests.secure_zone_policy._base import SecureZonePolicyBase

_HINTS_PATH = (Path(__file__).parent.parent.parent
               / "config" / "scan_hints" / "secure_zone_agent_policy.yaml")


class TestSecureZonePolicyScenario0Scan(SecureZonePolicyBase):
    """시큐어존 정책 — 신규/제거 UI 감지 (diff-only)."""

    def test_scenario0a_add_modal_diff(self, logged_in_page, settings):
        print("\n━━ [시큐어존 정책] 시나리오 0a: 신규/제거 UI 감지 (yaml baseline ↔ DOM) ━━━")
        page = SecureZoneAgentPolicyPage(logged_in_page, settings)
        self._page = page.page
        page.navigate_to()
        self._ensure_session_cleanup(page)

        hints = _yaml.safe_load(_HINTS_PATH.read_text(encoding="utf-8")) or {}
        context_sel = f"#{hints.get('modal_id', 'addItemModal')}.in"

        page.open_add_modal()
        try:
            yaml_set = extract_yaml_selectors(hints)
            dom_set  = extract_dom_selectors(page.page, context_sel)
            diff     = compare(yaml_set, dom_set)
            new_labels = extract_dom_labels(page.page, context_sel, diff["new"])
            new_attrs  = extract_dom_attributes(page.page, context_sel, diff["new"])
            yaml_labels = extract_yaml_labels(hints)
            # 숨김: yaml+DOM 둘 다 있으나 섹션 display:none (모달 열린 채 판정 — offsetParent 유효).
            #   gating(disabled)은 보임 → 제외 / 토글 스위치 self-hidden → 제외 / 비활성 탭 → 제외.
            hidden_sels = extract_dom_hidden(page.page, context_sel, diff["common"])
        finally:
            page._close_modal_if_open()   # 모달 닫기 (필드 클릭 없음 — singleton 안전)

        new_set, missing_set = diff["new"], diff["missing"]
        self._add("warn" if (new_set or missing_set or hidden_sels) else "pass",
                  "sc0a — 신규/제거/숨김 UI 감지 (yaml baseline ↔ 모달 DOM diff, 클릭 없음)",
                  f"baseline {len(yaml_set)}개 / DOM {len(dom_set)}개 → "
                  f"신규={len(new_set)}건, 제거={len(missing_set)}건, 숨김={len(hidden_sels)}건 "
                  f"(0/0/0 = UI 변동 없음)", sc=0)

        # 신규 요소 카드 — DOM 라벨/속성 동봉 (검수자가 yaml baseline 추가 판단)
        for sel in sorted(new_set):
            ko    = (new_labels.get(sel) or "").strip()
            attrs = new_attrs.get(sel) or {}
            t = attrs.get("type") or "?"
            ml = attrs.get("maxlength")
            self._add("warn",
                      f"sc0a — 🆕 신규 요소 [{t}] {ko or '(라벨 미추출)'} ({sel})",
                      f"DOM 존재 / yaml baseline 미정의. maxlength={ml}. "
                      f"검수자 조치: 의도된 추가면 yaml baseline 에 추가, 임시면 무시.", sc=0)

        # 제거 요소 카드 — 회귀 후보
        for sel in sorted(missing_set):
            ko = (yaml_labels.get(sel) or "").strip()
            self._add("warn",
                      f"sc0a — ❌ 제거 요소 {ko or ''} ({sel})",
                      "yaml baseline 에 있으나 DOM 에 없음 — 회귀 후보(요소 사라짐) 또는 의도된 제거.", sc=0)

        # 숨김 요소 카드 — yaml+DOM 둘 다 있으나 섹션 display:none (회귀 후보, sc3 가 skip 처리)
        for sel in sorted(hidden_sels):
            ko = (yaml_labels.get(sel) or "").strip()
            self._add("warn",
                      f"sc0a — 🙈 숨김 요소 {ko or ''} ({sel})",
                      "yaml baseline+DOM 둘 다 존재하나 섹션이 display:none — 회귀 후보(섹션 사라짐) "
                      "또는 환경별 숨김. sc3 동일 기준(feature_available)으로 자동 skip.", sc=0)
