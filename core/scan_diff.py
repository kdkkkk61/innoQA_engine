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

    # tab_* 문서 구조 (npouch_policy 등) — id+type 으로 baseline 구성.
    #   {tab_basic_info: {group: [{id, type}, ...]}, tab_pdf_protect: {...}}
    #   type 매핑: textarea→textarea# / select→select# / button→제외(폼요소 아님) / 그 외→input#
    #   tab_ 접두 key 가 있는 페이지(npouch)만 동작 — 다른 페이지 무영향(additive).
    _TAG_BY_TYPE = {"textarea": "textarea", "select": "select"}
    for _k, _v in hints.items():
        if not (isinstance(_k, str) and _k.startswith("tab_") and isinstance(_v, dict)):
            continue
        for _group in _v.values():
            if not isinstance(_group, list):
                continue
            for _item in _group:
                if not isinstance(_item, dict):
                    continue
                _fid = _item.get("id")
                _ft  = (_item.get("type") or "").lower()
                if not _fid or _ft == "button":
                    continue
                selectors.add(f"{_TAG_BY_TYPE.get(_ft, 'input')}#{_fid}")

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

    # tab_* 문서 구조 (npouch_policy 등) — id+label (extract_yaml_selectors 와 동일 규칙).
    # 삭제/숨김 카드에 한국어 명칭 표시용 (DOM 없어도 yaml 라벨로 식별 가능).
    _TAG_BY_TYPE = {"textarea": "textarea", "select": "select"}
    for _k, _v in hints.items():
        if not (isinstance(_k, str) and _k.startswith("tab_") and isinstance(_v, dict)):
            continue
        for _group in _v.values():
            if not isinstance(_group, list):
                continue
            for _item in _group:
                if not isinstance(_item, dict):
                    continue
                _fid = _item.get("id")
                _ft  = (_item.get("type") or "").lower()
                if not _fid or _ft == "button":
                    continue
                _lab = _item.get("label", "")
                if _lab:
                    out[f"{_TAG_BY_TYPE.get(_ft, 'input')}#{_fid}"] = _lab

    return out


# ── B-1-B-1: 신규 요소 자동 분류 + 임시 hints 확장 ────────────────────────────

# 자동 분류 결과를 기존 validators 재사용에 적합한 yaml 항목 형식으로 변환.
# 사용자 비전 B 핵심 — "신규 요소 발견 시 yaml 등록 없이도 시나리오 2 검증 자동".
#
# 안전 메커니즘 (추정 위험 완화):
#   - DOM에서 추출 가능한 정보만 사용 (label, type, maxlength, checked).
#   - DOM에 없는 정보(required, dependent_fields)는 안전 default (False, []).
#   - validator 결과 status는 호출자에서 warn 강제 가능.

# 자동 검증 시 사용할 표준 test_value (시나리오 2 동작 검증용 임시 값)
_AUTO_TEST_VALUE = "[AUTO]_seq"


def expand_hints_with_discovered(
    new_selectors: Iterable[str],
    attrs:         dict[str, dict],
    labels:        dict[str, str],
    tag_patterns:  dict[str, dict] | None = None,
) -> dict:
    """
    신규 발견 셀렉터들을 기존 validators가 처리할 수 있는 yaml 항목 형식으로 변환.

    반환:
      {
        "text_inputs":       [{selector, label, maxlength, required, test_value, order}, ...],
        "toggle_checkboxes": [{selector, label, default, dependent_fields, order}, ...],
        "plain_checkboxes":  [{selector, label, default, order}, ...],
        "radio_groups":      [{name, label, default, dependent_fields, options, order}, ...],
        "tag_input":         [{id, label, input, add_btn, container, remove_btn,
                               required, test_value, order}, ...],
      }

    호출자(ui_scanner)는 이 dict를 임시 hints로 사용해 _scan_from_hints 재호출.
    기존 yaml의 항목은 포함 안 됨 — 중복 검증 방지.

    안전 default:
      required = False (DOM에서 안 보임 — 보수적)
      dependent_fields = [] (자동 매칭 X — 단독 검증만)

    radio_groups 처리:
      - 신규 radio input 을 `name` 속성 으로 그룹화 (HTML radio 그룹 표준)
      - 그룹 라벨 = `name` 그대로 (DOM 라벨 추출 결과는 옵션 라벨이므로 그룹 라벨 별도 추출 X)
      - 각 옵션: {selector, value, label} — value/label 은 DOM 에서 추출
      - default = None (요구 안 함 — yaml-driven 영역)

    tag_input 처리 (`tag_patterns` 인자로 사전 탐지 결과 주입):
      - text 타입 input 중 `detect_tag_input_patterns` 로 매칭된 항목은 text_inputs 가 아니라
        tag_input 으로 분류 (추가/제거 동작 검증 가능).
      - 매칭 안 된 text input 은 일반 text_inputs 로 fallback.
      - tag_patterns=None 이면 모든 text input 을 text_inputs 로 처리 (이전 동작 호환).
    """
    text_inputs:       list[dict] = []
    toggle_checkboxes: list[dict] = []
    plain_checkboxes:  list[dict] = []
    tag_inputs_out:    list[dict] = []
    # radio: name 으로 그룹화 — {name: {options: [...], min_order: int}}
    radio_buckets:     dict[str, dict] = {}

    # 자동 분류 항목의 order 시작 — 시나리오 2 영역 끝 (다른 yaml 항목 뒤)
    base_order = 8000

    tag_patterns = tag_patterns or {}

    for i, sel in enumerate(sorted(new_selectors)):
        a   = attrs.get(sel) or {}
        lab = (labels.get(sel) or "").strip() or sel  # 라벨 없으면 셀렉터로 폴백
        t   = a.get("type", "")
        order = base_order + i

        # 화면에 안 보이는 입력 (탭 차단·display:none 등) 은 자동 분류 대상 외.
        # discovered_new 시나리오 1 카드는 별도 흐름이라 그대로 등록됨.
        # 자동 분류 (시나리오 2~5 검증 카드) 만 visible 기준으로 분리.
        # visible 키가 attrs 에 없으면 (구버전 호출) 기본 True 로 처리해 호환 유지.
        if not a.get("visible", True):
            continue

        if t in ("text", "textarea", "number", "password", "email"):
            # tag_input 패턴 매칭됐으면 tag_input 으로, 아니면 text_inputs fallback
            pat = tag_patterns.get(sel)
            if pat and pat.get("input") and pat.get("add_btn") and pat.get("container"):
                tag_inputs_out.append({
                    "id":         sel.replace("input#", "").replace("input", "") or sel,
                    "label":      lab,
                    "input":      pat["input"],
                    "add_btn":    pat["add_btn"],
                    "container":  pat["container"],
                    "remove_btn": pat.get("remove_btn") or "button.deleteBtn",
                    "required":   False,
                    "test_value": _AUTO_TEST_VALUE,
                    "order":      order,
                })
                continue
            text_inputs.append({
                "selector":   sel,
                "label":      lab,
                "maxlength":  a.get("maxlength"),  # None 가능
                "required":   False,               # DOM에서 모름 — 안전 default
                "test_value": _AUTO_TEST_VALUE,
                "order":      order,
            })
        elif t == "checkbox":
            entry = {
                "selector": sel,
                "label":    lab,
                "default":  bool(a.get("checked")),
                "order":    order,
            }
            # toggle 속성 있으면 toggle_checkboxes, 없으면 plain
            if a.get("has_toggle"):
                entry["dependent_fields"] = []  # 자동 매칭 X — 단독 검증만
                toggle_checkboxes.append(entry)
            else:
                plain_checkboxes.append(entry)
        elif t == "radio":
            grp_name = a.get("name") or ""
            if not grp_name:
                continue  # name 없으면 그룹 식별 불가 — 스킵
            bucket = radio_buckets.setdefault(grp_name, {
                "options":   [],
                "min_order": order,  # 그룹 order = 첫 옵션 order
            })
            bucket["options"].append({
                "selector": sel,
                "value":    a.get("value") or "",
                "label":    lab,
            })
        # select 등: 미지원

    # radio_buckets → radio_groups 항목 변환
    radio_groups: list[dict] = []
    for grp_name, bucket in radio_buckets.items():
        radio_groups.append({
            "name":             grp_name,
            "label":            grp_name,  # 그룹 라벨 = name (옵션 라벨이 아니라 그룹 식별자)
            "options":          bucket["options"],
            "default":          None,      # yaml-driven 영역, 자동 분류는 default 요구 X
            "dependent_fields": [],        # 자동 매칭 X — 단독 검증만
            "order":            bucket["min_order"],
        })

    return {
        "text_inputs":       text_inputs,
        "toggle_checkboxes": toggle_checkboxes,
        "plain_checkboxes":  plain_checkboxes,
        "radio_groups":      radio_groups,
        "tag_input":         tag_inputs_out,
    }


def extract_dom_attributes(page, context_sel: str, selectors: Iterable[str]) -> dict[str, dict]:
    """
    DOM 컨텍스트에서 각 셀렉터의 검증 관련 속성 추출.

    B-1-A 자동 검증의 안전 기준 = "DOM 속성 점검만, 동작 검증 X".
    클릭/입력 같은 데이터 변경 작업은 yaml 등록 후 정식 검증에서.

    추출 속성:
      type        : "text" | "checkbox" | "radio" | "number" | "textarea" | ...
      maxlength   : int | None  (text/textarea만)
      checked     : bool        (checkbox/radio만)
      disabled    : bool
      readonly    : bool
      has_toggle  : bool        (input의 'toggle' 커스텀 속성 여부 — 종속 패턴 힌트용)
      placeholder : str         (없으면 "")
      name        : str         (radio 그룹 식별용 — el.name property 사용. AngularJS
                                  동적 속성 대응. 없으면 "")
      value       : str         (radio 옵션 값용 — 없으면 "")
      visible     : bool        (현재 화면에 보이는지 — offsetParent + computed display.
                                  탭 차단 / display:none 등 안 보이는 입력 식별용)

    반환:
      {selector: {type, maxlength, checked, disabled, readonly, has_toggle,
                  placeholder, name, value, visible}}
      셀렉터를 못 찾으면 빈 dict (없는 게 아니라 모든 키가 None/빈값).
    """
    sel_list = list(selectors)
    if not context_sel or not sel_list:
        return {s: {} for s in sel_list}

    js = """
    (args) => {
        const root = document.querySelector(args.root_sel);
        if (!root) return {};
        const result = {};
        args.selectors.forEach(sel => {
            const el = root.querySelector(sel);
            if (!el) { result[sel] = {}; return; }
            const tag = el.tagName.toLowerCase();
            // 'type' 결정 — input은 type 속성, textarea/select는 태그명
            let type;
            if (tag === 'input') {
                type = (el.getAttribute('type') || 'text').toLowerCase();
            } else {
                type = tag;  // textarea, select
            }
            const ml = el.getAttribute('maxlength');
            // visible: offsetParent null 이면 display:none 또는 비활성 탭 등으로 안 보임
            const cs = window.getComputedStyle(el);
            const visible = el.offsetParent !== null
                          && cs.display !== 'none'
                          && cs.visibility !== 'hidden';
            result[sel] = {
                type:        type,
                maxlength:   ml ? parseInt(ml, 10) : null,
                checked:     !!el.checked,
                disabled:    !!el.disabled,
                readonly:    !!el.readOnly,
                has_toggle:  el.hasAttribute('toggle'),
                placeholder: el.getAttribute('placeholder') || '',
                // el.name property — AngularJS 동적 속성 대응. getAttribute 보다 견고.
                name:        el.name || el.getAttribute('name') || '',
                value:       el.value || el.getAttribute('value') || '',
                visible:     visible,
            };
        });
        return result;
    }
    """
    try:
        result = page.evaluate(js, {"root_sel": context_sel, "selectors": sel_list})
        if isinstance(result, dict):
            return {s: (result.get(s) or {}) for s in sel_list}
    except Exception:
        pass
    return {s: {} for s in sel_list}


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
            # 결과 정규화 (None 방지) + trailing 콜론/공백 정리
            # DOM 라벨이 "이름 :" 같이 콜론 포함된 경우 깔끔하게 표시
            return {
                s: (result.get(s) or "").strip().rstrip(":：").strip()
                for s in sel_list
            }
    except Exception:
        pass
    return {s: "" for s in sel_list}


def extract_dom_hidden(page, context_sel: str, selectors: Iterable[str]) -> list[str]:
    """yaml+DOM 둘 다 존재하는 셀렉터 중 '섹션 숨김(display:none)' 상태인 것만 반환.

    삭제(missing, DOM 미존재)와 구분되는 회귀 신호 — "있어야 할 게 화면에서 사라짐".
    판정 (core/ui_scanner.py 숨김 감지와 동일 기준):
      - offsetParent != null            → 보임 → 제외
      - 자신만 CSS 숨김(토글 스위치 raw input) → 부모 섹션 보임 → 제외
      - 구조적 부모가 display:none       → 숨김 (단, 비활성 탭 pane 은 제외=오탐 방지)

    매개변수:
      selectors : 비교 대상(보통 compare()['common'] = yaml ∩ DOM).
    반환:
      숨김 셀렉터 list (없으면 빈 list).
    """
    sel_list = list(selectors)
    if not context_sel or not sel_list:
        return []
    js = """
    (args) => {
        const [rootSel, sels] = args;
        const root = document.querySelector(rootSel);
        if (!root) return [];
        const out = [];
        for (const s of sels) {
            const el = root.querySelector(s);
            if (!el) continue;
            if (el.offsetParent !== null) continue;  // 명확히 보임 → 통과
            // offsetParent=null: (a)토글 스위치는 input 자체를 CSS로 숨김(부모는 보임)
            //   (b)섹션 display:none. 자신은 무시하고 '구조적 부모'가 숨김일 때만 섹션숨김.
            let node = el.parentElement, sectionHidden = false;
            while (node && node !== root) {
                const cs = getComputedStyle(node);
                if (cs.display === 'none') {
                    const isPane = node.classList.contains('modalBox')
                        || node.classList.contains('tab-pane')
                        || node.getAttribute('role') === 'tabpanel';
                    if (!isPane) sectionHidden = true;  // 구조적 섹션 숨김만
                    break;  // pane이면 비활성탭 → 제외(sectionHidden=false)
                }
                node = node.parentElement;
            }
            if (sectionHidden) out.push(s);
        }
        return out;
    }
    """
    try:
        result = page.evaluate(js, [context_sel, sel_list])
        return list(result) if isinstance(result, list) else []
    except Exception:
        return []


def detect_tag_input_patterns(
    page, context_sel: str, candidate_inputs: Iterable[str]
) -> dict[str, dict]:
    """
    텍스트 input 후보 중 "입력 > 추가 > 컨테이너 > 제거" 패턴 자동 탐지.

    기준 (`config/scan_hints/ransom_detect_policy.yaml` 의 기존 tag_input 4개 구조 분석):
      - container: input id 뒤에 "List" 붙인 div 또는 ul (예: protectExtensionList)
      - add button: 다음 우선순위
        1. id="add{InputIdCapitalized}" 형태 (예: addExceptFilePath)
        2. textContent="추가" 이면서 input 부모 3-level 안에 있는 button
      - remove button: container 내부 후보 — i.extentionDeleteBtn / button.deleteBtn /
        [ng-click*="delete"] / [ng-click*="remove"] 등 (기본값 button.deleteBtn)

    container + add button 둘 다 매칭되면 tag_input 후보로 반환.
    하나라도 매칭 안 되면 None (호출자가 일반 text_input 으로 처리).

    반환:
      {input_selector: {input, add_btn, container, remove_btn} | None, ...}
    """
    sel_list = list(candidate_inputs)
    if not context_sel or not sel_list:
        return {s: None for s in sel_list}

    js = """
    (args) => {
        const root = document.querySelector(args.root_sel);
        if (!root) return {};
        const result = {};
        args.inputs.forEach(sel => {
            const el = root.querySelector(sel);
            if (!el || el.tagName.toLowerCase() !== 'input') {
                result[sel] = null; return;
            }
            // input 안 보이면 (탭 차단 등) tag_input 매칭 안 함 — 회귀 가드.
            if (el.offsetParent === null) { result[sel] = null; return; }
            const id = el.id || '';
            if (!id) { result[sel] = null; return; }

            // ─ container: id + "List" (div or ul) ─
            let container = root.querySelector(`div#${id}List, ul#${id}List`);
            if (!container) { result[sel] = null; return; }

            // ─ add button ─
            let addBtn = null;
            const capId = id.charAt(0).toUpperCase() + id.slice(1);
            // pattern 1: button#add{Capitalized}
            let cand = root.querySelector(`button#add${capId}`);
            if (cand) addBtn = `button#add${capId}`;
            else {
                // pattern 2: textContent="추가" + parent 3-level 안 button
                const buttons = root.querySelectorAll('button');
                for (const b of buttons) {
                    if (b.textContent.trim() !== '추가' || !b.id) continue;
                    let p = el.parentElement;
                    for (let i = 0; i < 4 && p; i++) {
                        if (p.contains(b)) { addBtn = `button#${b.id}`; break; }
                        p = p.parentElement;
                    }
                    if (addBtn) break;
                }
            }
            if (!addBtn) { result[sel] = null; return; }

            // ─ remove button (container 내부 후보) ─
            const removeCandidates = [
                'i.extentionDeleteBtn',    // 앱 오탈자 보존
                'i.deleteBtn',
                'button.deleteBtn',
                '[ng-click*="delete"]',
                '[ng-click*="remove"]',
            ];
            let removeBtn = 'button.deleteBtn';  // 기본값
            for (const r of removeCandidates) {
                if (container.querySelector(r)) { removeBtn = r; break; }
            }

            const cTag  = container.tagName.toLowerCase();
            const cId   = container.id;
            result[sel] = {
                input:      sel,
                add_btn:    addBtn,
                container:  `${cTag}#${cId}`,
                remove_btn: removeBtn,
            };
        });
        return result;
    }
    """
    try:
        result = page.evaluate(js, {"root_sel": context_sel, "inputs": sel_list})
        if isinstance(result, dict):
            return {s: (result.get(s) or None) for s in sel_list}
    except Exception:
        pass
    return {s: None for s in sel_list}
