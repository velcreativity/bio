/**
 * 작품 설명 docx 빌더 — 레퍼런스 양식(캡션용 + 리플렛용) 고정.
 *
 *   npm install docx      # 최초 1회
 *   node build.js works/도구.json "작품설명_도구.docx"
 *
 * 양식 근거: 업로드된 작품 설명 PDF(<선택 매트릭스>/<방 안의 방>/<흐르는 동안>)
 *   A4 · 여백 2.5cm · 맑은 고딕 11pt · 본문 양쪽정렬 · 작품명 굵게+밑줄
 *   구조: 작품 설명 / 작품 옆 캡션용 / <제목> / 캡션 1문단 / (빈 줄) /
 *         리플렛용 / <제목> / 리플렛 3~4문단
 */
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, PageOrientation,
} = require("docx");
const fs = require("fs");
const path = require("path");

const FONT = { ascii: "맑은 고딕", eastAsia: "맑은 고딕", hAnsi: "맑은 고딕" };
const SIZE = 22;   // 11pt
const LINE = 330;  // ~1.38 행간
const GAP = 160;   // 문단 뒤 간격

const para = (text, opts = {}) =>
  new Paragraph({
    alignment: opts.justify ? AlignmentType.JUSTIFIED : AlignmentType.LEFT,
    spacing: { line: LINE, after: GAP },
    children: [
      new TextRun({
        text,
        font: FONT,
        size: SIZE,
        bold: opts.title || undefined,
        underline: opts.title ? {} : undefined,
      }),
    ],
  });

const [dataPath, outPath] = process.argv.slice(2);
if (!dataPath || !outPath) {
  console.error("usage: node build.js <work.json> <out.docx>");
  process.exit(1);
}
const w = JSON.parse(fs.readFileSync(dataPath, "utf8"));
const name = `<${w.title}>`;

const doc = new Document({
  sections: [
    {
      properties: {
        page: {
          size: { width: 11906, height: 16838, orientation: PageOrientation.PORTRAIT },
          margin: { top: 1418, right: 1418, bottom: 1418, left: 1418 },
        },
      },
      children: [
        para("작품 설명"),
        para("작품 옆 캡션용"),
        para(name, { title: true }),
        para(w.caption, { justify: true }),
        para(""),
        para("리플렛용"),
        para(name, { title: true }),
        ...w.leaflet.map((t) => para(t, { justify: true })),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, buf);
  const n = (s) => s.replace(/\s/g, "").length;
  console.log(`written: ${outPath}`);
  console.log(`  캡션용   ${n(w.caption)}자 (레퍼런스 189~229)`);
  console.log(`  리플렛용 ${n(w.leaflet.join(""))}자 (레퍼런스 554~713) 문단별 ${w.leaflet.map(n)}`);
});
