#!/usr/bin/env python3
"""hwpx_textdump.py — HWPX 텍스트 추출기 (계보 프로브·검증용).

사용법:
  python3 hwpx_textdump.py file.hwpx              # 전 섹션 텍스트 (문단당 1줄)
  python3 hwpx_textdump.py file.hwpx --grep 문자열 # 존재 확인 (계보 프로브)

핵심 규칙 (KB §4.2):
  - <hp:t ...속성>도 잡는다: <hp:t[^>]*>
  - 텍스트 내부의 중첩 태그를 제거한다
  - 놓치면 "이미 수정됨/안 됨" 오판이 발생한다 (실제 사고 사례)
"""
import re, sys, zipfile

def dump_section(xml_text):
    lines = []
    for p in re.split(r"<hp:p [^>]*>", xml_text):
        ts = re.findall(r"<hp:t[^>]*>(.*?)</hp:t>", p, re.S)
        txt = "".join(re.sub(r"<[^>]+>", "", t) for t in ts).strip()
        if txt:
            lines.append(txt)
    return lines

def main():
    path = sys.argv[1]
    needle = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--grep" else None
    z = zipfile.ZipFile(path)
    secs = sorted(n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n))
    hit = 0
    for sec in secs:
        lines = dump_section(z.read(sec).decode("utf-8"))
        for ln in lines:
            if needle:
                if needle in ln:
                    print(f"{sec}: {ln}")
                    hit += 1
            else:
                print(ln)
    if needle:
        print(f"-- '{needle}': {hit} paragraph(s)")
        sys.exit(0 if hit else 1)

if __name__ == "__main__":
    main()
