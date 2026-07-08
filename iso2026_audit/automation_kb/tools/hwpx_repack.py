#!/usr/bin/env python3
"""hwpx_repack.py — archive-clone 패키징 (R-PKG-1) + 구조 검증.

사용법:
  python3 hwpx_repack.py ORIGINAL.hwpx OUTPUT.hwpx Contents/section0.xml=edited0.xml [more=...]

절대 규칙 (KB §4.1 — 위반 시 Hancom "파일이 손상되었습니다"):
  - zip -r 재압축 금지. 원본 아카이브를 엔트리 단위로 복제한다.
  - 엔트리 순서/압축방식/속성 원본 그대로, 디렉터리 엔트리 0개.
  - 편집한 파일의 바이트만 교체한다.

검증까지 자동 수행: 엔트리 순서 동일, dir 엔트리 0, mimetype 선두 STORED,
편집 파일 XML well-formed, style-ref dangling 0.
"""
import re, sys, zipfile, xml.dom.minidom as M

def repack(src, out, edited):
    zin = zipfile.ZipFile(src)
    zout = zipfile.ZipFile(out, "w")
    for item in zin.infolist():
        data = edited.get(item.filename, zin.read(item.filename))
        if isinstance(data, str):
            data = data.encode("utf-8")
        ni = zipfile.ZipInfo(item.filename, date_time=item.date_time)
        ni.compress_type = item.compress_type
        ni.external_attr = item.external_attr
        ni.internal_attr = item.internal_attr
        ni.create_system = item.create_system
        zout.writestr(ni, data)
    zout.close(); zin.close()

def verify(src, out):
    zo, zv = zipfile.ZipFile(src), zipfile.ZipFile(out)
    a = [i.filename for i in zo.infolist()]
    b = [i.filename for i in zv.infolist()]
    assert a == b, f"entry order/set mismatch: {set(a) ^ set(b) or 'order differs'}"
    assert not any(n.endswith("/") for n in b), "directory entries present"
    first = zv.infolist()[0]
    assert first.filename == "mimetype" and first.compress_type == 0, "mimetype not stored-first"
    assert zv.testzip() is None, "CRC failure"
    # XML well-formed on all xml-ish parts
    for n in b:
        if n.endswith((".xml", ".hpf", ".rdf")):
            M.parseString(zv.read(n))
    # style-ref gate
    hdr = zv.read("Contents/header.xml").decode("utf-8")
    defs = {k: set(map(int, re.findall(p, hdr))) for k, p in [
        ("charPr", r'<hh:charPr id="(\d+)"'), ("paraPr", r'<hh:paraPr id="(\d+)"'),
        ("style", r'<hh:style id="(\d+)"'), ("borderFill", r'<hh:borderFill id="(\d+)"')]}
    for n in b:
        if re.fullmatch(r"Contents/section\d+\.xml", n):
            s = zv.read(n).decode("utf-8")
            for k, attr in [("charPr", "charPrIDRef"), ("paraPr", "paraPrIDRef"),
                            ("style", "styleIDRef"), ("borderFill", "borderFillIDRef")]:
                dang = set(map(int, re.findall(attr + r'="(\d+)"', s))) - defs[k]
                assert not dang, f"{n}: dangling {k} {sorted(dang)}"
    print("VERIFY PASS:", out)

if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    edited = {}
    for arg in sys.argv[3:]:
        entry, path = arg.split("=", 1)
        edited[entry] = open(path, "rb").read()
    repack(src, out, edited)
    verify(src, out)
