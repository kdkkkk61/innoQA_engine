"""태그 관리 시나리오 공통 base — 운용 프로세스 base 상속 (재구성 2026-07-03).

공통 자산(sub-numbering/merge_key/_shot/_replay_shots/_R 안전망/오버플로 헬퍼) 전부 상속.
차이: PAGE_ID / 오버플로 이름 필드(tagName). cleanup 은 페이지별 1회 플래그로 분리돼 있음.
"""
from tests.common.operation_process._base import OperationProcessBase, _ss, _SAVE_SUCCESS_KEYWORDS


class TagBase(OperationProcessBase):
    """태그 관리 공통 base."""

    PAGE_ID = "common_tag"
    NAME_FIELD_SEL_ATTR = "SEL_TAG_NAME"
    NAME_FIELD_ID = "tagName"
