#!/usr/bin/env python3
"""hwpx_cellfill.py — 셀 그리드 주소화 기입 엔진 (KB §4.4).

폼 채우기의 표준형. 라이브러리로 import해서 쓴다 (통보서 3건 실전 검증 패턴).

    from hwpx_cellfill import cell_grid, fill_cells, strip_lineseg
    doc = z.read("Contents/section0.xml").decode("utf-8")
    print(cell_grid(doc))                # 1) 그리드 조사: (row,col) -> 라벨/빈칸
    doc = fill_cells(doc, {              # 2) 주소로 기입 (뒤에서부터 자동 적용)
        (2, 3): "경영지원팀",
        (3, 6): "2026.06.10",
        (5, 2): "부적합사항 첫 줄",       #    멀티라인 = 연속 행의 셀에 한 줄씩
        (6, 2): "부적합사항 둘째 줄",
    })
    doc = strip_lineseg(doc)             # 3) 편집 후 레이아웃 캐시 제거 (KB §4.7)

규칙:
  - 빈 셀 패턴 <hp:run charPrIDRef="N"/>만 채운다. 같은 charPr id 재사용 (새 스타일 금지).
  - 대상 셀에 빈 run이 없으면 예외 발생 → 조사로 돌아가라. 절대 우회하지 마라.
  - 값의 & 는 &amp; 로 이스케이프해서 넘겨라 (KB §4.9).
  - 셀 폭(HWPU)÷1100 ≈ 글자수/줄. 넘치면 문안 단축 (KB §4.10).
"""
import re

EMPTY_RUN = re.compile(r'<hp:run charPrIDRef="(\d+)"\s*/>')

def cell_spans(doc):
    """(row,col) -> (start,end) 바이트 span. 폼 전체 tc 순회."""
    spans = {}
    for m in re.finditer(r"<hp:tc [^>]*>", doc):
        a = m.start()
        b = doc.find("</hp:tc>", a) + len("</hp:tc>")
        ad = re.search(r'colAddr="(\d+)" rowAddr="(\d+)"', doc[a:b])
        if ad:
            spans[(int(ad.group(2)), int(ad.group(1)))] = (a, b)
    return spans

def cell_grid(doc):
    """조사용: 정렬된 (row,col, colSpan/rowSpan, 텍스트, 빈run수) 목록 문자열."""
    rows = []
    for (r, c), (a, b) in sorted(cell_spans(doc).items()):
        cell = doc[a:b]
        sp = re.search(r'colSpan="(\d+)" rowSpan="(\d+)"', cell)
        txt = "".join(re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", cell, re.S))
        txt = re.sub(r"<[^>]+>", "", txt).strip()
        empty = len(EMPTY_RUN.findall(cell))
        rows.append(f"row{r:2d} col{c:2d} span={sp.groups() if sp else '?'} "
                    f"empty={empty} text={txt[:30]!r}")
    return "\n".join(rows)

def fill_cells(doc, fills):
    """fills: {(row,col): text}. 뒤쪽 셀부터 적용해 span 무효화를 방지."""
    spans = cell_spans(doc)
    missing = [rc for rc in fills if rc not in spans]
    if missing:
        raise KeyError(f"cells not found: {missing}")
    for rc in sorted(fills, key=lambda rc: spans[rc][0], reverse=True):
        a, b = spans[rc]
        cell = doc[a:b]
        m = EMPTY_RUN.search(cell)
        if not m:
            raise ValueError(f"no empty run in cell {rc} — re-survey the grid")
        run = f'<hp:run charPrIDRef="{m.group(1)}"><hp:t>{fills[rc]}</hp:t></hp:run>'
        doc = doc[:a] + cell[: m.start()] + run + cell[m.end():] + doc[b:]
    return doc

def strip_lineseg(doc):
    """편집한 섹션의 stale 레이아웃 캐시 전제거 (뷰어가 재계산)."""
    return re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", doc, flags=re.S)
