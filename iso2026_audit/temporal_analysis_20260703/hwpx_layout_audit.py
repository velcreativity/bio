#!/usr/bin/env python3
"""hwpx_layout_audit.py — HWPX 표 레이아웃 전수 측정 도구
사용: python3 hwpx_layout_audit.py <file.hwpx> [report.md]

섹션별 용지/여백/printable region, 표별 크기·위치·좌우간격·내부 구성(열폭/행높이/병합/여백)을
결정적 수치로 출력한다. AI에게 레이아웃 작업을 시키기 전 이 리포트를 기준값으로 고정하고,
작업 후 다시 돌려 diff가 의도한 항목뿐인지 확인하는 용도.

단위: HWPUNIT (1/7200 inch). mm = HWPUNIT / 283.465
"""
import re, sys, zipfile

MM = 283.465

def mm(v): return f"{v/MM:.1f}mm"

def outer_spans(s, tag):
    evs = sorted([(m.start(), 1) for m in re.finditer(rf'<hp:{tag}\b', s)] +
                 [(m.end(), -1) for m in re.finditer(rf'</hp:{tag}>', s)])
    out, d, st = [], 0, None
    for pos, dd in evs:
        if dd == 1 and d == 0: st = pos
        d += dd
        if d == 0 and dd == -1: out.append((st, pos))
    return out

TXT = re.compile(r'<hp:t(?:\s[^>]*)?>(.*?)</hp:t>', re.S)

def first_text(blob, n=30):
    for t in TXT.findall(blob):
        ft = re.sub(r'<[^>]+>', '', t)
        ft = re.sub(r'[\U000F0000-\U000FFFFD]', '', ft).strip()
        if ft: return ft[:n]
    return ''

def audit_table(blob, printW, zone):
    tag = re.match(r'<hp:tbl\b[^>]*>', blob).group(0)
    g = lambda k, d='?': (re.search(rf'{k}="([^"]*)"', tag) or [None, d])[1]
    szm = re.search(r'<hp:sz\b[^>]*width="(\d+)"[^>]*height="(\d+)"', blob)
    w, h = int(szm.group(1)), int(szm.group(2))
    pos = re.search(r'<hp:pos\b[^>]*/>', blob)
    pg = lambda k: (re.search(rf'{k}="([^"]*)"', pos.group(0)) or [None, '?'])[1] if pos else '?'
    im = re.search(r'<hp:inMargin\b[^>]*/>', blob)
    rows = outer_spans(blob, 'tr')
    # 행별 열폭 벡터 + 경계 일관성
    row_infos, boundaries = [], set()
    for a, b in rows:
        tr = blob[a:b]
        cells = re.findall(r'<hp:cellSpan[^>]*colSpan="(\d+)"[^>]*rowSpan="(\d+)"[^>]*/>\s*<hp:cellSz[^>]*width="(\d+)"[^>]*height="(\d+)"', tr)
        ws = [int(c[2]) for c in cells]
        # 행높이 = rowSpan=1 셀의 높이 (병합 셀은 여러 행 합산 높이라 제외)
        h1 = [int(c[3]) for c in cells if c[1] == '1']
        hs = h1 if h1 else [int(c[3]) for c in cells]
        spans = [(c[0], c[1]) for c in cells]
        cum = 0; bset = []
        for x in ws: cum += x; bset.append(cum)
        boundaries.add(tuple(bset[:-1]))
        row_infos.append((ws, min(hs) if hs else 0, spans))
    merged = sum(1 for _, _, sp in row_infos for c, r in sp if int(c) > 1 or int(r) > 1)
    hsum = sum(rh for _, rh, _ in row_infos)
    lines = []
    lines.append(f"  [{zone}] {g('rowCnt')}x{g('colCnt')} \"{first_text(blob)}\"")
    lines.append(f"    크기: w={w}({mm(w)}) h={h}({mm(h)}) | 행높이합={hsum}({mm(hsum)})"
                 + (" ⚠주의: sz높이≠행합" if abs(hsum-h) > 20 else ""))
    over = "⚠폭초과!" if w > printW else "OK"
    gap = printW - w
    lines.append(f"    페이지 내: printW={printW} → 좌우 여유 합={gap}({mm(gap)}) | 중앙정렬 시 좌=우={gap//2}({mm(gap//2)}) [{over}]")
    lines.append(f"    개체속성: 글자처럼취급={pg('treatAsChar')} 쪽영역제한(flowWithText)={pg('flowWithText')} "
                 f"겹침허용={pg('allowOverlap')} 가로정렬={pg('horzAlign')} 세로기준={pg('vertRelTo')}")
    lines.append(f"    표속성: 쪽경계나눔={g('pageBreak')} 제목행반복={g('repeatHeader')} 배치={g('textWrap')} 테두리ID={g('borderFillIDRef')}")
    if im: lines.append(f"    셀 안여백: {im.group(0).replace('<hp:inMargin ','').replace('/>','')}")
    ws0 = row_infos[0][0]
    lines.append(f"    1행 열폭: {ws0} (합={sum(ws0)})")
    if len(boundaries) > 1:
        lines.append(f"    열 경계 변형: 행마다 경계 {len(boundaries)}종 (병합/이형 행 존재 — 정상일 수 있음)")
    lines.append(f"    행높이: {[rh for _, rh, _ in row_infos]}")
    if merged: lines.append(f"    병합 셀: {merged}개 (colSpan/rowSpan>1)")
    return lines

def main(path, out=None):
    z = zipfile.ZipFile(path)
    secs = sorted([n for n in z.namelist() if re.match(r'Contents/section\d+\.xml', n)],
                  key=lambda n: int(re.search(r'(\d+)', n).group()))
    R = [f"# HWPX 레이아웃 측정 리포트: {path}", ""]
    for sn in secs:
        s = z.read(sn).decode('utf-8')
        si = int(re.search(r'(\d+)', sn).group())
        pp = re.search(r'<hp:pagePr[^>]*landscape="(\w+)"[^>]*width="(\d+)"[^>]*height="(\d+)"', s)
        land, pw, ph = pp.group(1), int(pp.group(2)), int(pp.group(3))
        if land == 'NARROWLY': pw, ph = ph, pw
        mg = re.search(r'<hp:margin[^>]*/>', s).group(0)
        gm = lambda k: int(re.search(rf'{k}="(\d+)"', mg).group(1))
        printW = pw - gm('left') - gm('right') - gm('gutter')
        printH = ph - gm('top') - gm('bottom')
        bodyH = printH - gm('header') - gm('footer')
        R.append(f"## 섹션 {si} — 용지 {'가로' if land=='NARROWLY' else '세로'} {pw}x{ph} ({mm(pw)} x {mm(ph)})")
        R.append(f"- 여백: 좌{gm('left')} 우{gm('right')} 상{gm('top')} 하{gm('bottom')} | 머리말밴드 {gm('header')} 꼬리말밴드 {gm('footer')} 제본 {gm('gutter')}")
        R.append(f"- **printable region: 폭 {printW}({mm(printW)}) x 높이 {printH}({mm(printH)})** | 본문영역 높이(밴드 제외) {bodyH}({mm(bodyH)})")
        hf = []
        for kind in ('header', 'footer'):
            for a, b in [(m.start(), m.end()) for m in re.finditer(rf'<hp:{kind}\b.*?</hp:{kind}>', s, re.S)]:
                hf.append((a, b, '머리말' if kind == 'header' else '꼬리말'))
        def zone_of(p):
            for a, b, k in hf:
                if a <= p < b: return k
            return '본문'
        n = 0
        for a, b in outer_spans(s, 'tbl'):
            R += audit_table(s[a:b], printW, f"표{n}·{zone_of(a)}")
            R.append("")
            n += 1
    rep = "\n".join(R)
    if out: open(out, 'w', encoding='utf-8').write(rep)
    print(rep)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
