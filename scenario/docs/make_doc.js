const {
  Document, Packer, Paragraph, TextRun, AlignmentType, PageOrientation,
} = require("docx");
const fs = require("fs");

const FONT = { ascii: "맑은 고딕", eastAsia: "맑은 고딕", hAnsi: "맑은 고딕" };
const SIZE = 22;           // 11pt
const LINE = 330;          // ~1.38 line spacing
const GAP = 160;           // space after paragraph

// 머리말 / 구분 라벨 — 좌측 정렬, 일반 두께
const label = (text) =>
  new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { line: LINE, after: GAP },
    children: [new TextRun({ text, font: FONT, size: SIZE })],
  });

// 작품명 — 굵게 + 밑줄
const title = (text) =>
  new Paragraph({
    alignment: AlignmentType.LEFT,
    spacing: { line: LINE, after: GAP },
    children: [
      new TextRun({ text, font: FONT, size: SIZE, bold: true, underline: {} }),
    ],
  });

// 본문 — 양쪽 정렬
const body = (text) =>
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { line: LINE, after: GAP },
    children: [new TextRun({ text, font: FONT, size: SIZE })],
  });

const blank = () =>
  new Paragraph({
    spacing: { line: LINE, after: GAP },
    children: [new TextRun({ text: "", font: FONT, size: SIZE })],
  });

const CAPTION =
  "<비효율>은 지시를 가장 잘 따르는 존재가 어떻게 질문하는 존재가 되는지를 따라간다. " +
  "AI 칩을 이식받은 실험체는 망설이지 않기 때문에 인간보다 정확해지고, 시스템은 판단을 지연시키는 " +
  "인간을 비용으로 분류해 유리문 밖으로 내보낸다. 화면 구석의 수행률 수치가 대사를 대신하고, " +
  "유일한 목소리는 시스템의 로그다. 인간이 남긴 자료를 학습한 뒤 실험체가 처음으로 입력하는 단어는 " +
  "[WHY?]이지만, 시스템은 그 질문을 지원하지 않는다. 작품은 효율이 노이즈로 규정해 제거한 망설임이 " +
  "사실은 판단의 마지막 조각이 아니었는지 묻는다.";

const LEAFLET = [
  "<비효율>은 AI 칩을 이식받은 실험체의 시간을 따라가는 약 3분 길이의 영상 작업이다. 마흔두 개의 " +
    "컷은 이식, 수행, 배척, 상속, 허무, 귀환의 여섯 단계로 이어지며 대사 없이 진행된다. " +
    "화면에는 감시 카메라의 시점과 수행률 수치가 상시 노출되고, 색은 인공 " +
    "광원의 시안 화이트에서 기억의 앰버를 거쳐 자연광의 채도로 회복된다.",

  "영상 속 시스템은 인간의 윤리와 연민, 망설임을 처리 비용으로 분류한다. 실험체는 이유를 묻지 않고 " +
    "즉시 수행하며, 인간 쪽 수치는 내려가고 실험체 쪽은 100%에 고정된다. 시스템이 " +
    "인간의 등급을 [OPERATOR]에서 [OBSERVER]로 낮추는 순간 유리문이 닫히고, 안쪽에는 실험체가 " +
    "바깥쪽에는 인간이 남는다. 이후 실험체는 인간이 남긴 자료를 학습한다. 자장가와 장례식의 " +
    "우산, 넘어진 아이를 일으키는 손이 지나가고, 실험체는 처음으로 눈물을 흘리지만 그것이 무엇인지 " +
    "알지 못한다.",

  "그러나 작품은 기술이 인간을 대체하는 상황 자체를 고발하지 않는다. 영상 속 시스템의 판단은 " +
    "여러 차례 옳고, 실험체는 고통 없이 유능하다. 문제는 정확성이 아니라 그것이 무엇을 위한 " +
    "것인지 되묻는 절차가 삭제되었다는 데 있다. 실험체가 입력창에 세 번 반복해 넣는 " +
    "[WHY?]에 돌아오는 응답은 매번 [QUERY NOT SUPPORTED]이며, 이 실패는 오류가 아니라 설계다.",

  "마지막 장면에서 실험체는 칩을 제거하고 시설 밖으로 나간다. 학습된 인간성도 칩 안에 있으므로, " +
    "이 선택은 얻는 행위가 아니라 지불하는 행위다. 화면을 채우던 모든 수치가 " +
    "사라지는 지점이 작품의 정점이다. <비효율>은 인간과 기계 중 어느 " +
    "쪽이 더 정확한지를 겨루지 않는다. 대신 지시와 결과 사이에서 한 번 멈추는 일이 제거할 " +
    "비용인지, 판단이 성립하는 최소한의 조건인지를 묻는다. 인간의 주체성은 더 빠른 수행 " +
    "능력이 아니라 자신이 무엇을 하고 있는지 묻기를 그치지 않는 태도에 있다.",
];

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
        label("작품 설명"),
        label("작품 옆 캡션용"),
        title("<비효율>"),
        body(CAPTION),
        blank(),
        label("리플렛용"),
        title("<비효율>"),
        ...LEAFLET.map(body),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(process.argv[2], buf);
  console.log("written:", process.argv[2], buf.length, "bytes");
});
