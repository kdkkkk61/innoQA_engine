"""
core/scan_diff.py — DOM 스캔 ↔ yaml 정의 비교 헬퍼

시나리오 1 (UI 구조)의 회귀 본질 부분 — 기능 추가/제거 감지.

상세 정의:
  - docs/scenario_1_ui.md "DOM 스캔 + yaml 비교" 섹션
  - docs/test_scenario_standard.md "책임 분리 매트릭스 (회귀 본질)"

사용 시점:
  - modal_form: ui_scanner._scan_from_hints 호출 후 (모달이 열린 상태)
  - list_page : list_page_runner 시나리오 1 단계

원칙 (md 작성 규칙 준수):
  - Karpathy 2 (Simplicity): 함수 5개. 추상화 X.
  - Karpathy 3 (Surgical): 호출자 ScanResult 변환은 별도. 본 헬퍼는 비교/추출만.
  - 추정 금지: yaml의 명시된 셀렉터만 추출. 추정으로 type 매핑 X.
  - 이모지 금지: 콘솔/로그 CP949 환경에서 깨짐 (TROUBLESHOOTING "BUG 낙음" 케이스).
                 한국어 텍스트만 사용. HTML 리포트 측 status_badge가 아이콘 처리.
"""
from __future__ import annotations

from typing import Iterable


# ── yaml 셀렉터 추출 ──────────────────────────────────────────────────────────

def extract_yaml_selectors(hints: dict) -> set[str]:
    """
    yaml hints의 모든 폼 요소 셀렉터를 평면화하여 set 반환.

    추출 대상 섹션 (현재 yaml 구조 — config/scan_hints/*.yaml 기반):
      modal_form:
        - text_inputs[].selector
        - radio_groups[].options[].selector
        - radio_groups[].dependent_fields[].selector
        - plain_checkboxes[].selector
        - toggle_checkboxes[].selector
        - toggle_checkboxes[].dependent_fields[] (str or {selector: ...})
        - tag_input[].input
      list_page:
        - add_modal.fields[].selector

    반환:
      셀렉터 문자열 set. 예: {'input#policyName', 'input#isConnect', ...}
    """
    selectors: set[str] = set()
    if not hints:
        return selectors

    # text_inputs (modal_form)
    for ti in hints.get("text_inputs", []) or []:
        sel = ti.get("selector") if isinstance(ti, dict) else None
        if sel:
            selectors.add(sel)

    # radio_groups (modal_form)
    for rg in hints.get("radio_groups", []) or []:
        if not isinstance(rg, dict):
            continue
        for opt in rg.get("options", []) or []:
            sel = opt.get("selector") if isinstance(opt, dict) else None
            if sel:
                selectors.add(sel)
        for dep in rg.get("dependent_fields", []) or []:
            sel = dep.get("selector") if isinstance(dep, dict) else None
            if sel:
                selectors.add(sel)

    # plain_checkboxes (modal_form)
    for cb in hints.get("plain_checkboxes", []) or []:
        sel = cb.get("selector") if isinstance(cb, dict) else None
        if sel:
            selectors.add(sel)

    # toggle_checkboxes (modal_form)
    for tg in hints.get("toggle_checkboxes", []) or []:
        if not isinstance(tg, dict):
            continue
        sel = tg.get("selector")
        if sel:
            selectors.add(sel)
        # dependent_fields: str 또는 dict
        for dep in tg.get("dependent_fields", []) or []:
            if isinstance(dep, str):
                selectors.add(dep)
            elif isinstance(dep, dict):
                d_sel = dep.get("selector")
                if d_sel:
                    selectors.add(d_sel)

    # tag_input (modal_form) — input 필드만 비교 대상.
    # add_btn(button#...), container(div#/ul#...), remove_btn은 폼 요소가 아니라
    # 액션·컨테이너 요소. DOM 자동 탐지 대상(input/textarea/select)과 결이 달라
    # 비교에 포함하면 false positive 발생 (DOM에 안 잡혀 "제거됨"으로 오분류).
    for tg in hints.get("tag_input", []) or []:
        if not isinstance(tg, dict):
            continue
        sel = tg.get("input")
        if sel:
            selectors.add(sel)

    # add_modal.fields (list_page)
    add_modal = hints.get("add_modal") or {}
    if isinstance(add_modal, dict):
        for f in add_modal.get("fields", []) or []:
            sel = f.get("selector") if isinstance(f, dict) else None
            if sel:
                selectors.add(sel)

    # 비교 대상은 폼 입력 요소 한정. button/div/ul 등 액션·컨테이너는 제외.
    # extract_dom_selectors 가 input/textarea/select 만 반환하므로 일치시킴.
    return {
        s for s in selectors
        if s.startswith(("input#", "textarea#", "select#"))
    }


# ── DOM 자동 탐지 ────────────────────────────────────────────────────────────

def extract_dom_selectors(page, context_sel: str) -> set[str]:
    """
    DOM 컨텍스트(모달 등)의 폼 요소를 자동 추출하여 set 반환.

    대상:
      input  (id 있는 것, type=hidden/button/submit/reset 제외)
      textarea (id 있는 것)
      select (id 있는 것)

    반환:
      '{tag}#{id}' 형식 셀렉터 set. 예: {'input#policyName', 'textarea#description'}

    매개변수:
      page         : Playwright Page 객체
      context_sel  : 컨텍스트 CSS selector (예: 'div#addItemModal.in')
                     이 컨텍스트 하위 요소만 스캔.
    """
    selectors: set[str] = set()
    if not context_sel:
        return selectors

    # JavaScript로 한 번에 추출 (Playwright locator 반복보다 빠름)
    js = """
    (root_sel) => {
        const root = document.querySelector(root_sel);
        if (!root) return [];
        const out = [];
        const SKIP_INPUT_TYPES = new Set(['hidden', 'button', 'submit', 'reset']);

        root.querySelectorAll('input').forEach(el => {
            if (!el.id) return;
            const t = (el.getAttribute('type') || 'text').toLowerCase();
            if (SKIP_INPUT_TYPES.has(t)) return;
            out.push('input#' + el.id);
        });
        root.querySelectorAll('textarea').forEach(el => {
            if (!el.id) return;
            out.push('textarea#' + el.id);
        });
        root.querySelectorAll('select').forEach(el => {
            if (!el.id) return;
            out.push('select#' + el.id);
        });
        return out;
    }
    """
    try:
        result = page.evaluate(js, context_sel)
        if isinstance(result, list):
            selectors.update(result)
    except Exception:
        # 컨텍스트 미존재 / 페이지 상태 이상 등 — 빈 set 반환
        pass

    return selectors


# ── 비교 ─────────────────────────────────────────────────────────────────────

def compare(yaml_set: Iterable[str], dom_set: Iterable[str]) -> dict:
    """
    yaml 정의 셀렉터 set과 DOM 추출 셀렉터 set 비교.

    반환:
      {
        'new':     set[str],  # DOM에만 존재 (yaml 미정의) — 신규 요소 가능성
        'missing': set[str],  # yaml에만 존재 (DOM 미발견) — 제거 요소 가능성
        'common':  set[str],  # 둘 다 존재 (정상 — 다른 시나리오에서 검증됨)
      }
    """
    y = set(yaml_set)
    d = set(dom_set)
    return {
        "new":     d - y,
        "missing": y - d,
        "common":  d & y,
    }


# ── 라벨 추출 (한국어 의미 파악용) ────────────────────────────────────────────

def extract_yaml_labels(hints: dict) -> dict[str, str]:
    """
    yaml hints에서 셀렉터 → 한국어 label 매핑 추출.

    extract_yaml_selectors 와 같은 섹션 순회. label 필드가 있으면 매핑.
    discovered_missing 카드에 사람이 읽을 수 있는 의미 표시용.

    반환:
      {selector: label} 매핑. 라벨 없으면 빈 문자열.
    """
    out: dict[str, str] = {}
    if not hints:
        return out

    # text_inputs
    for ti in hints.get("text_inputs", []) or []:
        if isinstance(ti, dict):
            sel = ti.get("selector"); lab = ti.get("label", "")
            if sel:
                out[sel] = lab

    # radio_groups - options
    for rg in hints.get("radio_groups", []) or []:
        if not isinstance(rg, dict):
            continue
        rg_label = rg.get("label", "")
        for opt in rg.get("options", []) or []:
            if not isinstance(opt, dict):
                continue
            sel = opt.get("selector")
            opt_lab = opt.get("label", "")
            if sel:
                out[sel] = f"{rg_label} - {opt_lab}".strip(" -") if rg_label else opt_lab

    # plain_checkboxes
    for cb in hints.get("plain_checkboxes", []) or []:
        if isinstance(cb, dict):
            sel = cb.get("selector"); lab = cb.get("label", "")
            if sel:
                out[sel] = lab

    # toggle_checkboxes
    for tg in hints.get("toggle_checkboxes", []) or []:
        if isinstance(tg, dict):
            sel = tg.get("selector"); lab = tg.get("label", "")
            if sel:
                out[sel] = lab

    # tag_input — input 키만
    for tg in hints.get("tag_input", []) or []:
        if isinstance(tg, dict):
            sel = tg.get("input"); lab = tg.get("label", "")
            if sel:
                out[sel] = lab

    # add_modal.fields (list_page)
    add_modal = hints.get("add_modal") or {}
    if isinstance(add_modal, dict):
        for f in add_modal.get("fields", []) or []:
            if isinstance(f, dict):
                sel = f.get("selector"); lab = f.get("label", "")
                if sel:
                    out[sel] = lab

    return out


def extract_dom_labels(page, context_sel: str, selectors: Iterable[str]) -> dict[str, str]:
    """
    DOM 컨텍스트에서 각 셀렉터의 한국어 label 추출.

    discovered_new 카드에 사람이 읽을 수 있는 의미 표시용
    (yaml에 정의 없는 신규 요소라 yaml 라벨 없음 → DOM에서 가져옴).

    추출 우선순위 (페이지 구조마다 다름 — 가장 흔한 패턴부터):
      1. <label for="{id}">텍스트</label>
      2. 부모 <label> 텍스트
      3. aria-label 속성
      4. placeholder 속성

    반환:
      {selector: label} 매핑. 라벨 못 찾으면 빈 문자열.
    """
    sel_list = list(selectors)
    if not context_sel or not sel_list:
        return {s: "" for s in sel_list}

    js = """
    (args) => {
        const root = document.querySelector(args.root_sel);
        if (!root) return {};
        const result = {};
        args.selectors.forEach(sel => {
            const el = root.querySelector(sel);
            if (!el) { result[sel] = ''; return; }

            // 1. <label for="{id}">
            if (el.id) {
                const labelEl = root.querySelector('label[for="' + el.id + '"]');
                if (labelEl) {
                    const txt = (labelEl.textContent || '').trim();
                    if (txt) { result[sel] = txt; return; }
                }
            }

            // 2. 부모 <label>
            const parentLabel = el.closest && el.closest('label');
            if (parentLabel) {
                const txt = (parentLabel.textContent || '').trim();
                if (txt) { result[sel] = txt; return; }
            }

            // 3. aria-label
            const aria = el.getAttribute && el.getAttribute('aria-label');
            if (aria) { result[sel] = aria.trim(); return; }

            // 4. placeholder
            const ph = el.getAttribute && el.getAttribute('placeholder');
            if (ph) { result[sel] = ph.trim(); return; }

            result[sel] = '';
        });
        return result;
    }
    """
    try:
        result = page.evaluate(js, {"root_sel": context_sel, "selectors": sel_list})
        if isinstance(result, dict):
            # 결과 정규화 (None 방지)
            return {s: (result.get(s) or "") for s in sel_list}
    except Exception:
        pass
    return {s: "" for s in sel_list}
