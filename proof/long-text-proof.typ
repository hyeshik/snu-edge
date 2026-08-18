#set page(
  paper: "a4",
  margin: (x: 18mm, y: 16mm),
  numbering: "1",
  number-align: bottom + right,
)
#set text(
  font: "DejaVu Sans",
  size: 10.5pt,
  fill: rgb("202124"),
  top-edge: 0.82em,
  bottom-edge: -0.22em,
)
#set par(justify: false, leading: 0.62em)

#let ink = rgb("202124")
#let muted = rgb("62666d")
#let faint = rgb("d9dce1")
#let panel = rgb("f7f8fa")
#let accent = rgb("2257c7")

#let styles = (
  (name: "Thin", edge-weight: 100, latin-weight: 285),
  (name: "Light", edge-weight: 300, latin-weight: 355),
  (name: "Regular", edge-weight: 400, latin-weight: 420),
  (name: "Medium", edge-weight: 500, latin-weight: 475),
  (name: "SemiBold", edge-weight: 600, latin-weight: 535),
  (name: "Bold", edge-weight: 700, latin-weight: 585),
  (name: "ExtraBold", edge-weight: 800, latin-weight: 645),
  (name: "Black", edge-weight: 900, latin-weight: 690),
)
#let style-by-name(name) = styles.find(item => item.name == name)
#let sentence-space = 0.25
#let ko(body) = (script: "cjk", body: body)
#let en(body) = (script: "latin", body: body)
#let finish(body) = (script: "finish", body: body)

#let edge(body, style, italic: false, size: 10.5pt) = text(
  font: "SNU Edge",
  weight: style.edge-weight,
  style: if italic { "italic" } else { "normal" },
  size: size,
  body,
)

#let latin-phrase(body, style, italic: false, size: 10.5pt) = edge(
  body, style, italic: italic, size: size,
)

#let latin-cjk-guard(style, terminal, italic, size) = {
  if italic {
    let y-guards = (
      Thin: 40, Light: 45, Regular: 45, Medium: 50,
      SemiBold: 50, Bold: 55, ExtraBold: 55, Black: 65,
    )
    let f-guards = (
      Thin: 105, Light: 110, Regular: 110, Medium: 115,
      SemiBold: 110, Bold: 115, ExtraBold: 110, Black: 115,
    )
    let units = if terminal == "y" {
      y-guards.at(style.name)
    } else if terminal == "f" {
      f-guards.at(style.name)
    } else if terminal == "l" and style.name == "Black" {
      30
    } else {
      20
    }
    h(size * units / 1000)
  }
}

#let mixed(segments, style, italic: false, size: 10.5pt) = {
  let pieces = segments.enumerate().map(entry => {
    let index = entry.at(0)
    let segment = entry.at(1)
    let segment-script = if segment.script == "finish" { "cjk" } else { segment.script }
    let previous = if index > 0 {
      segments.at(index - 1)
    } else {
      none
    }
    let previous-script = if previous == none {
      none
    } else if previous.script == "finish" {
      "cjk"
    } else {
      previous.script
    }
    let boundary = if previous == none or previous.script == "finish" {
      none
    } else if previous-script == "cjk" and segment-script == "latin" {
      h(size * 0.215)
    } else if previous-script == "latin" and segment-script == "cjk" {
      latin-cjk-guard(
        style,
        previous.body.clusters().last(),
        italic,
        size,
      )
    }
    let rendered = if segment.script == "cjk" {
      edge(segment.body, style, italic: italic, size: size)
    } else if segment.script == "finish" {
      let characters = segment.body.clusters()
      let prefix = characters.slice(0, characters.len() - 1).join()
      let terminal = characters.last()
      [#edge(prefix, style, italic: italic, size: size)#box[#edge(terminal, style, italic: italic, size: size)#edge(".", style, italic: italic, size: size)#h(size * sentence-space)]]
    } else {
      latin-phrase(segment.body, style, italic: italic, size: size)
    }
    [#boundary#rendered]
  })
  pieces.join()
}

#let section-title(kicker, title, note: none) = [
  #text(size: 7.5pt, weight: 700, fill: accent)[#kicker]
  #v(1mm)
  #text(size: 20pt, weight: 700, fill: ink)[#title]
  #if note != none [
    #v(1mm)
    #text(size: 8pt, fill: muted)[#note]
  ]
  #v(5mm)
]

#let paragraph(body, style: style-by-name("Regular"), italic: false, size: 10.5pt) = [
  #mixed(body, style, italic: italic, size: size)
  #parbreak()
]

#let p1 = (
  ko("연구팀은 새로운"), en("language model"), ko("을 실제 서비스에 배포하기 전에 다양한"),
  en("benchmark dataset"), finish("으로 성능을 검증했다"), ko("단일 점수만 비교하면 모델의 장단점을 놓치기 쉬우므로"),
  en("inference latency"), ko("와"), en("token throughput"), finish("뿐 아니라 메모리 사용량과 오류 유형도 함께 기록했다"),
)
#let p2 = (
  ko("평가 과정에서는 입력 길이와"), en("batch size"), finish("를 단계적으로 바꾸면서 결과가 안정적으로 유지되는지 확인했다"), ko("특히 긴 문서에서"),
  en("attention pattern"), ko("이 달라지는 현상과 작은 표본에서"), en("error rate"), finish("가 크게 흔들리는 현상을 분리해 분석했다"), ko("모든 실험에는 동일한"),
  en("random seed"), finish("와 환경 정보를 남겨 다른 연구자가 결과를 재현할 수 있도록 했다"),
)
#let p3 = (
  ko("데이터를 준비할 때에는 자동화된"), en("data pipeline"), finish("만 신뢰하지 않고 원문 표본을 직접 읽었다"), ko("정규화 단계에서 전문용어의 대소문자가 사라지거나"),
  en("version number"), finish("가 날짜로 잘못 해석되는 사례가 있었기 때문이다"), ko("수정된 규칙은"), en("unit test"), ko("와"),
  en("regression test"), finish("에 추가했으며 변경 전후의 통계량을 보고서에 함께 제시했다"),
)
#let p4 = (
  finish("실제 운영 환경에서는 평균 성능보다 실패가 발생하는 경계를 이해하는 일이 중요하다"), ko("연구자는"),
  en("monitoring dashboard"), ko("에서 지연 시간의 분포와 요청별"), en("GPU memory"), finish("사용량을 관찰하고 경고 기준을 조정했다"), ko("갑작스러운"),
  en("traffic spike"), ko("가 발생했을 때에는 작은 모델로 요청을 전환하는"), en("fallback policy"), finish("가 정상적으로 작동하는지도 점검했다"),
)
#let p5 = (
  finish("결과를 해석할 때에는 통계적으로 유의한 차이와 실제 사용자가 체감하는 차이를 구분했다"),
  en("confidence interval"), finish("이 좁더라도 화면에서 문장이 끊기거나 응답 순서가 바뀌면 서비스 품질은 낮아질 수 있다"), ko("따라서 정량 평가 뒤에는 연구자가 직접"),
  en("error analysis"), finish("를 수행하고 대표 사례를 유형별로 정리했다"),
)
#let p6 = (
  finish("공동 연구를 진행할 때에는 코드와 데이터뿐 아니라 판단의 근거도 공유해야 한다"), ko("각 실험의"),
  en("commit hash"), ko("와 설정 파일을 기록하고 중요한 결정은 짧은"), en("design note"), finish("로 남겼다"), ko("회의에서는 최신 결과만 보여주지 않고 실패한"),
  en("baseline model"), finish("과 중단한 접근법도 함께 검토해 같은 시행착오가 반복되지 않도록 했다"),
)
#let p7 = (
  finish("논문 초안을 작성하면서 연구팀은 그림과 표의 용어를 본문과 통일했다"), en("training schedule"), ko("과"),
  en("evaluation protocol"), finish("처럼 반복되는 표현은 처음 등장할 때 정의하고 이후에는 같은 표기를 유지했다"), finish("독자가 결과를 빠르게 확인할 수 있도록 각 절의 첫 문장에는 핵심 주장과 적용 범위를 명확히 적었다"),
)
#let p8 = (
  finish("최종 검토에서는 작은 화면과 인쇄물에서 동일한 문단을 읽어 보았다"), ko("화면에서는"), en("anti aliasing"), finish("과 글자 간 리듬을 살피고 인쇄물에서는 획의 농도와 줄 사이의 균형을 확인했다"), finish("한글과 영문이 연속해서 나타나는 문장에서도 어느 한쪽이 지나치게 튀지 않는지를 중심으로 판단했다"),
)

// Cover
#align(center + horizon)[
  #text(size: 8pt, weight: 700, fill: accent)[SNU EDGE · PRODUCTION OTF]
  #v(4mm)
  #text(size: 27pt, weight: 750)[Long-form mixed-script proof]
  #v(3mm)
  #text(size: 11pt, fill: muted)[NanumSquare CJK × Montserrat Latin]
  #v(10mm)
  #block(width: 135mm, inset: 6mm, fill: panel, stroke: 0.5pt + faint, radius: 2mm)[
    #grid(
      columns: (43mm, 1fr),
      row-gutter: 2.5mm,
      [#text(weight: 700)[Weight match]], [round density],
      [#text(weight: 700)[Width]], [86%],
      [#text(weight: 700)[Height / baseline]], [New B · 102.8% / yShift −26],
      [#text(weight: 700)[Spacing]], [proportional q 0.90],
      [#text(weight: 700)[Script boundary]], [CJK→Latin 0.215em · Latin→CJK attached],
    )
  ]
]

#pagebreak()
#section-title(
  "01 · REGULAR UPRIGHT",
  "긴 호흡의 기술 문서",
  note: "Regular 400 / Montserrat 420 · 10.5 pt · two-column reading measure",
)
#columns(2, gutter: 9mm)[
  #paragraph(p1)
  #paragraph(p2)
  #paragraph(p3)
  #paragraph(p4)
  #paragraph(p5)
  #paragraph(p6)
  #paragraph(p7)
  #paragraph(p8)
]

#pagebreak()
#section-title(
  "02 · REGULAR UPRIGHT",
  "넓은 판면에서의 문단 리듬",
  note: "Regular 400 / Montserrat 420 · 12 pt · single column",
)
#align(center)[
  #block(width: 142mm)[
    #align(left)[
      #paragraph(p1, size: 12pt)
      #paragraph(p2, size: 12pt)
      #paragraph(p4, size: 12pt)
      #paragraph(p5, size: 12pt)
      #paragraph(p7, size: 12pt)
    ]
  ]
]

#pagebreak()
#section-title(
  "03 · BODY WEIGHT",
  "Light · Regular · Medium",
  note: "The same long paragraph at three text weights; all use New B and q 0.90.",
)
#for name in ("Light", "Regular", "Medium") [
  #let selected = style-by-name(name)
  #block(width: 100%, inset: 4mm, fill: panel, stroke: 0.4pt + faint, radius: 1.5mm)[
    #text(size: 7pt, weight: 700, fill: accent)[#name · Edge #selected.edge-weight / Montserrat #selected.latin-weight]
    #v(2mm)
    #mixed(p3, selected, size: 10.5pt)
    #parbreak()
    #mixed(p6, selected, size: 10.5pt)
  ]
  #v(4mm)
]

#pagebreak()
#section-title(
  "04 · TRUE ITALIC",
  "기울임이 섞인 긴 문장",
  note: "Latin→CJK remains attached; true italic adds a terminal-specific measured overhang guard.",
)
#columns(2, gutter: 9mm)[
  #paragraph(p1, italic: true)
  #paragraph(p2, italic: true)
  #paragraph(p3, italic: true)
  #paragraph(p4, italic: true)
  #paragraph(p5, italic: true)
  #paragraph(p6, italic: true)
  #paragraph(p7, italic: true)
  #paragraph(p8, italic: true)
]

#pagebreak()
#section-title(
  "05 · DOCUMENT HIERARCHY",
  "제목과 본문을 함께 읽기",
  note: "Selected round-density weights across a realistic report hierarchy.",
)
#text(font: "SNU Edge", weight: 700, size: 22pt)[재현 가능한 모델 평가]
#v(2mm)
#mixed((ko("실험 설계와"), en("deployment monitoring"), ko("을 연결하는 방법")), style-by-name("Bold"), size: 13pt)
#v(6mm)
#mixed((en("1."), ko("데이터와 평가 기준")), style-by-name("SemiBold"), size: 14pt)
#v(2mm)
#paragraph(p1)
#paragraph(p3)
#v(2mm)
#mixed((en("2."), ko("운영 환경의 관찰")), style-by-name("SemiBold"), size: 14pt)
#v(2mm)
#paragraph(p4)
#paragraph(p5)
#v(3mm)
#block(width: 100%, inset: 4mm, fill: panel, radius: 1.5mm)[
  #text(size: 7pt, weight: 700, fill: accent)[NOTE · LIGHT 300 / MONTSERRAT 355]
  #v(1.5mm)
  #mixed(p6, style-by-name("Light"), size: 9pt)
]

#pagebreak()
#section-title(
  "06 · FAMILY COLOR",
  "모든 weight의 긴 문장 농도",
  note: "Each row uses its selected round-density Montserrat instance.",
)
#for (index, selected) in styles.enumerate() [
  #block(width: 100%, inset: (x: 3mm, y: 2.2mm), fill: if calc.rem(index, 2) == 0 { panel } else { white })[
    #grid(
      columns: (27mm, 1fr),
      gutter: 3mm,
      [
        #text(size: 7pt, weight: 700)[#selected.name]
        #linebreak()
        #text(size: 6pt, fill: muted)[#selected.edge-weight / #selected.latin-weight]
      ],
      [#mixed(p8, selected, size: 8.5pt)],
    )
  ]
]

#pagebreak()
#section-title(
  "07 · SMALL TEXT",
  "작은 크기에서의 연속 읽기",
  note: "Long text at 8.5 pt and 9.5 pt; inspect counters, punctuation, and mixed-script word boundaries.",
)
#grid(
  columns: (1fr, 1fr),
  gutter: 8mm,
  [
    #text(size: 7pt, weight: 700, fill: accent)[8.5 PT · REGULAR]
    #v(2mm)
    #paragraph(p1, size: 8.5pt)
    #paragraph(p2, size: 8.5pt)
    #paragraph(p3, size: 8.5pt)
    #paragraph(p4, size: 8.5pt)
    #paragraph(p5, size: 8.5pt)
    #paragraph(p6, size: 8.5pt)
  ],
  [
    #text(size: 7pt, weight: 700, fill: accent)[9.5 PT · REGULAR]
    #v(2mm)
    #paragraph(p3, size: 9.5pt)
    #paragraph(p4, size: 9.5pt)
    #paragraph(p5, size: 9.5pt)
    #paragraph(p6, size: 9.5pt)
    #paragraph(p7, size: 9.5pt)
    #paragraph(p8, size: 9.5pt)
  ],
)
