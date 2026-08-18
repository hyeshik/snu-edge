#set page(
  width: 297mm,
  height: 210mm,
  margin: (x: 12mm, y: 10mm),
  numbering: "1",
  number-align: bottom + right,
)
#set text(font: "DejaVu Sans", size: 9pt, fill: rgb("202124"))
#set par(leading: 0.55em)

#let ink = rgb("202124")
#let muted = rgb("62666d")
#let faint = rgb("d9dce1")
#let panel = rgb("f7f8fa")
#let accent = rgb("2257c7")

#let styles = (
  (
    name: "Thin", edge-weight: 100, chosen: 285,
    candidates: (
      (weight: 285, reason: "round density"),
      (weight: 288, reason: "H stem @ 86%"),
      (weight: 290, reason: "overall ink"),
      (weight: 320, reason: "stem-text high"),
    ),
  ),
  (
    name: "Light", edge-weight: 300, chosen: 355,
    candidates: (
      (weight: 355, reason: "ink / round"),
      (weight: 361, reason: "H stem @ 86%"),
      (weight: 390, reason: "stem-text high"),
    ),
  ),
  (
    name: "Regular", edge-weight: 400, chosen: 420,
    candidates: (
      (weight: 415, reason: "overall ink"),
      (weight: 419, reason: "H stem @ 86%"),
      (weight: 420, reason: "round density"),
      (weight: 455, reason: "stem-text high"),
    ),
  ),
  (
    name: "Medium", edge-weight: 500, chosen: 475,
    candidates: (
      (weight: 465, reason: "overall ink"),
      (weight: 475, reason: "round density"),
      (weight: 478, reason: "H stem @ 86%"),
      (weight: 510, reason: "stem-text high"),
    ),
  ),
  (
    name: "SemiBold", edge-weight: 600, chosen: 535,
    candidates: (
      (weight: 525, reason: "overall ink"),
      (weight: 535, reason: "round density"),
      (weight: 537, reason: "H stem @ 86%"),
      (weight: 565, reason: "stem-text high"),
    ),
  ),
  (
    name: "Bold", edge-weight: 700, chosen: 585,
    candidates: (
      (weight: 570, reason: "overall ink"),
      (weight: 585, reason: "round density"),
      (weight: 588, reason: "H stem @ 86%"),
      (weight: 605, reason: "stem-text high"),
    ),
  ),
  (
    name: "ExtraBold", edge-weight: 800, chosen: 645,
    candidates: (
      (weight: 625, reason: "overall ink"),
      (weight: 640, reason: "H stem @ 86%"),
      (weight: 645, reason: "round density"),
      (weight: 660, reason: "stem-text high"),
    ),
  ),
  (
    name: "Black", edge-weight: 900, chosen: 690,
    candidates: (
      (weight: 665, reason: "overall ink"),
      (weight: 688, reason: "H stem @ 86%"),
      (weight: 690, reason: "round density"),
      (weight: 695, reason: "stem-text high"),
    ),
  ),
)

#let proof-title(section, title, note: none) = [
  #text(size: 7.5pt, weight: 700, fill: accent)[#section]
  #v(0.8mm)
  #text(size: 17pt, weight: 700, fill: ink)[#title]
  #if note != none [
    #v(0.8mm)
    #text(size: 8pt, fill: muted)[#note]
  ]
  #v(3mm)
]

#let montserrat(
  body,
  weight: 400,
  italic: false,
  size: 20pt,
  width: 100%,
  tracking: 0,
  vertical-adjust: false,
  features: (),
) = {
  // `tracking` is the final post-scale delta in 1/1000 em.
  let inverse-width = if width == 84% {
    100 / 84
  } else if width == 86% {
    100 / 86
  } else if width == 88% {
    100 / 88
  } else {
    1
  }
  let face = text(
    font: "Montserrat",
    weight: weight,
    style: if italic { "italic" } else { "normal" },
    size: size,
    tracking: tracking * inverse-width * 0.001em,
    features: features,
    body,
  )
  let transformed = scale(
    x: width,
    y: if vertical-adjust { 102.8% } else { 100% },
    origin: left + bottom,
    reflow: true,
    face,
  )
  if vertical-adjust {
    // Font-space yShift -26 at UPM 1000 is +0.026em in page coordinates.
    move(dy: 0.026em, transformed)
  } else {
    transformed
  }
}

#let spacing-audit = json("generated/montserrat-spacing-audit.json")
#let h-weight-audit = json("generated/h-stroke-weight-audit.json")

#let spacing-run(style, italic) = spacing-audit.styles.find(run =>
  run.style == style.name and run.posture == if italic { "italic" } else { "upright" }
)

#let proportional-word(word, style, spacing-scale, italic: false, size: 12pt) = {
  let run = spacing-run(style, italic)
  let characters = word.clusters()
  let pieces = characters.enumerate().map(entry => {
    let index = entry.at(0)
    let character = entry.at(1)
    let glyph = box(montserrat(
      character,
      weight: style.chosen,
      italic: italic,
      size: size,
      width: 86%,
    ))
    if index + 1 < characters.len() {
      let pair = character + characters.at(index + 1)
      let layout-record = run.layout_pairs.at(pair, default: none)
      let record = if layout-record != none {
        layout-record
      } else {
        (run.proof_pairs + run.matrix_pairs).find(item => item.pair == pair)
      }
      let delta = 0.86 * (record.kern + (spacing-scale - 1) * record.bbox_gap)
      [#glyph#h(size * delta / 1000)]
    } else {
      glyph
    }
  })
  box(pieces.join())
}

#let proportional-line(line, style, spacing-scale, italic: false, size: 12pt) = {
  let words = line.split(" ")
  let pieces = words.enumerate().map(entry => {
    let index = entry.at(0)
    let word = proportional-word(
      entry.at(1),
      style,
      spacing-scale,
      italic: italic,
      size: size,
    )
    if index + 1 < words.len() {
      [#word#h(size * 0.25 * 0.86 * spacing-scale)]
    } else {
      word
    }
  })
  box(pieces.join())
}

#let edge(body, weight: 400, italic: false, size: 20pt) = text(
  font: "SNU Edge v1 Reference",
  weight: weight,
  style: if italic { "italic" } else { "normal" },
  size: size,
  body,
)

#let specimen-card(label, line-one, line-two: none) = block(
  width: 100%,
  inset: (x: 3mm, y: 1.7mm),
  fill: panel,
  stroke: 0.45pt + faint,
  radius: 1.5mm,
)[
  #text(size: 7pt, weight: 600, fill: muted)[#label]
  #v(0.5mm)
  #line-one
  #if line-two != none [
    #v(-0.4mm)
    #line-two
  ]
]

#let weight-column(style, italic: false) = [
  #text(size: 8pt, weight: 700)[#if italic [Italic] else [Upright]]
  #v(1mm)
  #specimen-card(
    "SNU Edge v1 reference · nominal " + str(style.edge-weight),
    edge([Hamburgefontsiv RPB], weight: style.edge-weight, italic: italic, size: 22pt),
    line-two: edge([EDGE 0123456789], weight: style.edge-weight, italic: italic, size: 13pt),
  )
  #for candidate in style.candidates [
    #v(1.2mm)
    #specimen-card(
      "Montserrat wght " + str(candidate.weight) + " · " + candidate.reason,
      montserrat([Hamburgefontsiv RPB], weight: candidate.weight, italic: italic, size: 22pt, width: 86%),
      line-two: montserrat([EDGE 0123456789], weight: candidate.weight, italic: italic, size: 13pt, width: 86%),
    )
  ]
]

#let width-cell(style, width, tracking) = block(
  width: 100%,
  height: 35mm,
  inset: 2.5mm,
  fill: panel,
  stroke: 0.45pt + faint,
  radius: 1.5mm,
)[
  #let width-label = if width == 84% { "84%" } else if width == 86% { "86%" } else { "88%" }
  #text(size: 7pt, weight: 650, fill: muted)[width #width-label · tracking #if tracking > 0 [+]#str(tracking)]
  #v(1mm)
  #montserrat([Hamburgefontsiv RPB], weight: style.chosen, size: 17pt, width: width, tracking: tracking)
  #v(0.5mm)
  #montserrat([EDGE 012345], weight: style.chosen, size: 11pt, width: width, tracking: tracking)
]

#let mixed-copy = [연구팀은 새로운 language model을 benchmark dataset으로 평가했습니다. 실제 서비스에서는 GPU memory, inference latency와 token throughput을 함께 측정해 배포 설정을 조정합니다. 연구자는 error rate와 실험 로그를 검토해 다음 training schedule을 결정하고 최종 proof를 공유합니다.]

#let italic-cjk-guard(style, terminal, italic, size) = {
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

#let mixed-paragraph(style, vertical-adjust: false, italic: false, size: 14pt) = {
  let korean(body) = edge(
    body,
    weight: style.edge-weight,
    italic: italic,
    size: size,
  )
  let latin(body) = montserrat(
    body,
    weight: style.chosen,
    italic: italic,
    size: size,
    width: 86%,
    tracking: -5,
    vertical-adjust: vertical-adjust,
  )
  [#box[#korean([연구팀은 새로운])] #box[#latin([language model])]#italic-cjk-guard(style, "l", italic, size)#box[#korean([을])] #box[#latin([benchmark dataset])]#italic-cjk-guard(style, "t", italic, size)#box[#korean([으로 평가했습니다])]#box[#latin([.])] #box[#korean([실제 서비스에서는])] #box[#latin([GPU memory, inference latency])]#italic-cjk-guard(style, "y", italic, size)#box[#korean([와])] #box[#latin([token throughput])]#italic-cjk-guard(style, "t", italic, size)#box[#korean([을 함께 측정해 배포 설정을 조정합니다])]#box[#latin([.])] #box[#korean([연구자는])] #box[#latin([error rate])]#italic-cjk-guard(style, "e", italic, size)#box[#korean([와 실험 로그를 검토해 다음])] #box[#latin([training schedule])]#italic-cjk-guard(style, "e", italic, size)#box[#korean([을 결정하고 최종])] #box[#latin([proof])]#italic-cjk-guard(style, "f", italic, size)#box[#korean([를 공유합니다])]#box[#latin([.])]]
}

#let script-gap(size) = h(0.215 * size)

#let mixed-phrase(style, size: 12pt) = box()[
  #box[#edge([대규모], weight: style.edge-weight, size: size)]#script-gap(size)#box[#montserrat(
      [language model],
      weight: style.chosen,
      size: size,
      width: 86%,
      tracking: -5,
    )]#box[#edge([의 성능 평가], weight: style.edge-weight, size: size)]
]

#let mixed-figure-line(style, size: 13pt) = box()[
  #box[#montserrat([GPU memory 24 GB], weight: style.chosen, size: size, width: 86%, tracking: -5)]#box[#edge([와], weight: style.edge-weight, size: size)]#script-gap(size)#box[#montserrat([inference latency 18 ms], weight: style.chosen, size: size, width: 86%, tracking: -5)]#box[#edge([를 측정합니다], weight: style.edge-weight, size: size)]#box[#montserrat([.], weight: style.chosen, size: size, width: 86%, tracking: -5)]
]

#let paragraph-row(label, body, shade: false) = block(
  width: 100%,
  height: 36mm,
  inset: (x: 2.5mm, y: 2.2mm),
  fill: if shade { panel } else { white },
  stroke: 0.35pt + faint,
  radius: 1mm,
)[
  #grid(
    columns: (38mm, 1fr),
    gutter: 2mm,
    align: (left, top),
    [#text(size: 6.8pt, weight: 650, fill: muted)[#label]],
    [
      #set text(font: "SNU Edge v1 Reference", size: 14pt, top-edge: 0.82em, bottom-edge: -0.22em)
      #set par(leading: 0.48em)
      #body
    ],
  )
]

// Cover
#align(center + horizon)[
  #text(size: 9pt, weight: 700, fill: accent)[SNU EDGE SANS · DESIGN PROOF]
  #v(3mm)
  #text(size: 28pt, weight: 750)[NanumSquare CJK × Montserrat Latin]
  #v(2mm)
  #text(size: 13pt, fill: muted)[Weight · Width · Tracking · Mixed-script paragraphs]
  #v(10mm)
  #grid(
    columns: (35mm, 37mm, 37mm, 37mm),
    gutter: 1.5mm,
    align: (left, center, center, center),
    [#text(weight: 700)[Edge style]],
    [#text(weight: 700)[candidate wght]],
    [#text(weight: 700)[selected]],
    [#text(weight: 700)[nominal]],
    ..styles.map(style => (
      [#style.name],
      [#style.candidates.map(candidate => str(candidate.weight)).join(" / ")],
      [#style.chosen],
      [#style.edge-weight],
    )).flatten(),
  )
  #v(8mm)
  #text(size: 8pt, fill: muted)[Montserrat 9.000 variable fonts · UPM 1000 · proof width baseline 86%]
]

// Method and reading guide
#pagebreak()
#proof-title(
  "00 · GUIDE",
  "How to read this proof",
  note: "The selected round-density mapping is used downstream; alternative candidates remain visible for reference.",
)
#grid(
  columns: (1fr, 1fr),
  gutter: 8mm,
  [
    #text(size: 11pt, weight: 700)[Weight candidates]
    #v(2mm)
    #text(fill: muted)[
      • overall ink: ASCII letter/digit ink area per advance width\
      • round density: Oo068 group\
      • H stem @ 86%: measured H vertical stem after horizontal compression\
      • stem-text high: deliberately heavier upper control
    ]
    #v(5mm)
    #text(size: 11pt, weight: 700)[Width and tracking]
    #v(2mm)
    #text(fill: muted)[
      The 3×3 matrix tests 84/86/88% width and −10/0/+10 units per em. Tracking labels denote the final post-scale delta.
    ]
  ],
  [
    #text(size: 11pt, weight: 700)[Vertical alternatives]
    #v(2mm)
    #text(fill: muted)[
      A · native Montserrat geometry\
      B · 102.8% vertical scale, yShift −26 font units
    ]
    #v(5mm)
    #text(size: 11pt, weight: 700)[Decision order]
    #v(2mm)
    #text(fill: muted)[
      1. Compare local stem and round color at 22 pt.\
      2. Check text color at 13 pt.\
      3. Reject widths that distort rounded forms.\
      4. Check mixed Korean/Latin baseline and punctuation.\
      5. Confirm the result at small screen sizes.
    ]
  ],
)

// Weight proof: one page per Edge style, upright and italic together.
#for style in styles [
  #pagebreak()
  #proof-title(
    "01 · WEIGHT MATCH",
    style.name + " · candidate comparison",
    note: "All Montserrat samples use 86% width and zero added tracking. Reference is the proof-only SNU Edge v1 family.",
  )
  #grid(
    columns: (1fr, 1fr),
    gutter: 7mm,
    weight-column(style),
    weight-column(style, italic: true),
  )
]

// Width/tracking proof: complete 3×3 grid for every style.
#let widths = (84%, 86%, 88%)
#let trackings = (-10, 0, 10)
#for style in styles [
  #pagebreak()
  #proof-title(
    "02 · WIDTH × TRACKING",
    style.name + " · Montserrat wght " + str(style.chosen),
    note: "Selected round-density match. Compare line length, counter shape, and spacing rhythm. The raw 100% control is shown above the matrix.",
  )
  #grid(
    columns: (29mm, 1fr, 1fr),
    gutter: 3mm,
    align: (left, left, left),
    [#text(size: 7pt, weight: 700, fill: muted)[V1 · SNU EDGE SANS]],
    [#edge([Hamburgefontsiv RPB · EDGE 012345], weight: style.edge-weight, size: 15pt)],
    [#text(size: 7pt, weight: 700, fill: muted)[MONTSERRAT RAW 100% / 0]\
     #montserrat([Hamburgefontsiv RPB · EDGE 012345], weight: style.chosen, size: 15pt)],
  )
  #v(3mm)
  #for width in widths [
    #grid(
      columns: (1fr, 1fr, 1fr),
      gutter: 3mm,
      ..trackings.map(tracking => width-cell(style, width, tracking)),
    )
    #v(2.4mm)
  ]
]

// Mixed-script paragraph proof, one posture per page. Explicit text edges and
// paragraph leading neutralize source-font line metrics in every comparison.
#for style in styles [
  #for italic in (false, true) [
    #let posture = if italic { "italic" } else { "upright" }
    #pagebreak()
    #proof-title(
      "03 · MIXED-SCRIPT PARAGRAPH",
      style.name + " · " + posture,
      note: if italic {
        "Italic Latin→upright Hangul guards use measured post-transform overhangs. Text edges and leading remain fixed."
      } else {
        "Natural technical prose; cross-script word spaces use the SNU Edge 0.215em advance. Text edges and leading remain fixed."
      },
    )
    #block(width: 100%, inset: 3.2mm, stroke: 0.45pt + faint, radius: 1.5mm)[
      #paragraph-row(
        "V1 · SNU EDGE SANS",
        edge(mixed-copy, weight: style.edge-weight, italic: italic, size: 14pt),
        shade: true,
      )
      #v(1.5mm)
      #paragraph-row(
        "NEW A · NATIVE",
        mixed-paragraph(style, italic: italic),
      )
      #v(1.5mm)
      #paragraph-row(
        "NEW B · 102.8% / −26",
        mixed-paragraph(style, vertical-adjust: true, italic: italic),
        shade: true,
      )
    ]
  ]
]

// Small-size and family rhythm.
#pagebreak()
#proof-title(
  "04 · SIZE LADDER",
  "SNU Edge v1 reference × new proposal",
  note: "The new proposal uses 86% width, −5 tracking, and native vertical geometry. Compare antialiasing, counters, and mixed-script color.",
)
#grid(
  columns: (24mm, 15mm, 1fr, 1fr),
  gutter: 2mm,
  [], [],
  [#text(size: 7pt, weight: 700, fill: muted)[V1 · SNU EDGE SANS]],
  [#text(size: 7pt, weight: 700, fill: accent)[NEW · MONTSERRAT LATIN]],
)
#v(1.5mm)
#for style in styles [
  #grid(
    columns: (24mm, 15mm, 1fr, 1fr),
    gutter: 2mm,
    align: (left, right, left, left),
    [#text(size: 7pt, weight: 700)[#style.name]],
    [#text(size: 7pt, fill: muted)[9 pt]],
    [#edge([대규모 language model의 성능 평가], weight: style.edge-weight, size: 9pt)],
    [#mixed-phrase(style, size: 9pt)],
    [], [#text(size: 7pt, fill: muted)[12 pt]],
    [#edge([대규모 language model의 성능 평가], weight: style.edge-weight, size: 12pt)],
    [#mixed-phrase(style, size: 12pt)],
    [], [#text(size: 7pt, fill: muted)[16 pt]],
    [#edge([대규모 language model의 성능 평가], weight: style.edge-weight, size: 16pt)],
    [#mixed-phrase(style, size: 16pt)],
  )
  #v(2mm)
]

#pagebreak()
#proof-title(
  "05 · FIGURES & PUNCTUATION",
  "SNU Edge v1 reference × new figures and punctuation",
  note: "Compare the SNU Edge v1 reference with Montserrat defaults and tabular figures before choosing retained OpenType features.",
)
#for style in (styles.at(2), styles.at(5), styles.at(7)) [
  #block(width: 100%, inset: 3mm, stroke: 0.45pt + faint, radius: 1.5mm)[
    #text(size: 9pt, weight: 700)[#style.name]
    #v(1.5mm)
    #grid(
      columns: (30mm, 1fr),
      row-gutter: 1.5mm,
      [#text(size: 7pt, fill: muted)[V1]],
      [#edge([0123456789 · 2026/08/17 · ₩1,234,567], weight: style.edge-weight, size: 16pt)],
      [#text(size: 7pt, fill: muted)[NEW · DEFAULT]],
      [#montserrat([0123456789 · 2026/08/17 · ₩1,234,567], weight: style.chosen, size: 16pt, width: 86%, tracking: -5)],
      [#text(size: 7pt, fill: muted)[NEW · TABULAR `tnum`]],
      [#montserrat([0123456789 · 2026/08/17 · ₩1,234,567], weight: style.chosen, size: 16pt, width: 86%, tracking: -5, features: ("tnum",))],
      [#text(size: 7pt, fill: muted)[NEW · MIXED]],
      [#mixed-figure-line(style, size: 13pt)],
    )
  ]
  #v(4mm)
]

// Spacing-system audit. The proportional samples preserve native kerning while
// multiplying only bbox sidebearings and kerning; contour recessions stay at
// the selected 86% outline width.
#pagebreak()
#proof-title(
  "06 · SPACING SYSTEM",
  "From additive tracking to proportional spacing",
  note: "The machine audit screens every pair in the 99-character core repertoire at all eight weights and both postures.",
)
#let screened-pairs = spacing-audit.styles.map(run => run.pairs_screened).sum()
#grid(
  columns: (1fr, 1fr),
  gutter: 7mm,
  [
    #block(width: 100%, inset: 3mm, fill: panel, stroke: 0.4pt + faint, radius: 1.5mm)[
      #text(size: 10pt, weight: 700)[Verified shaping facts]
      #v(2mm)
      #text(fill: muted)[
        • #screened-pairs pair/style/posture cases screened\
        • GPOS `kern` lookups resolve only to PairPos type 2\
        • numeric pair positioning is context-independent\
        • ligatures and combining marks remain separate cases
      ]
    ]
    #v(4mm)
    #block(width: 100%, inset: 3mm, stroke: 0.4pt + faint, radius: 1.5mm)[
      #text(size: 10pt, weight: 700)[Discarded additive control]
      #v(2mm)
      #text(font: "DejaVu Sans Mono", size: 9pt)[gap′ = 0.86 × native gap − 5]
      #v(2mm)
      #text(fill: muted)[The same 5-unit subtraction is proportionally strongest on pairs that were already tight.]
    ]
  ],
  [
    #block(width: 100%, inset: 3mm, fill: panel, stroke: 0.4pt + faint, radius: 1.5mm)[
      #text(size: 10pt, weight: 700)[Selected production model]
      #v(2mm)
      #text(font: "DejaVu Sans Mono", size: 8.5pt)[gap′ = 0.86 × (contour recession + q × bbox gap)]
      #v(2mm)
      #text(fill: muted)[`bbox gap` is RSB(left) + LSB(right) + native kern. Curved and diagonal contour recessions are not treated as tracking.]
    ]
    #v(4mm)
    #block(width: 100%, inset: 3mm, stroke: 0.4pt + faint, radius: 1.5mm)[
      #text(size: 10pt, weight: 700)[Why this generalizes]
      #v(2mm)
      #text(fill: muted)[A single q applies to every retained glyph and every native kerning pair. Large sidebearing gaps shrink more in absolute units; small gaps and shape-created white space move less.]
    ]
  ],
)
#v(6mm)
#text(size: 10pt, weight: 700)[Packaging boundary]
#v(2mm)
#text(fill: muted)[
  The core audit covers Latin letters, figures, and Korean-use punctuation. Montserrat exposes #spacing-audit.coverage.spacing_characters spacing characters in total, including extended Latin, Cyrillic, modifiers, and symbols. The general rule can transform all of them mechanically, but unaudited scripts must either retain upstream spacing unchanged or be excluded from the declared SNU Edge repertoire until reviewed.
]

#pagebreak()
#proof-title(
  "06 · CLEARANCE SCREEN",
  "Pairs found outside the sample prose",
  note: "Negative horizontal-profile clearance is a screening signal, not proof of an ink collision. Compare the current and proportional models at larger sizes.",
)
#let clearance-lines = (
  "fY f¥ fV fT KY KA Kx £A kA",
  "Ax AX KV Qj XA VY YV",
)
#for style in (styles.at(2), styles.at(7)) [
  #for italic in (false, true) [
    #let posture = if italic { "italic" } else { "upright" }
    #block(width: 100%, inset: 2.5mm, fill: panel, stroke: 0.4pt + faint, radius: 1.5mm)[
      #grid(
        columns: (26mm, 1fr, 1fr),
        gutter: 3mm,
        [#text(size: 8pt, weight: 700)[#style.name · #posture]],
        [#text(size: 6.8pt, weight: 700, fill: accent)[CURRENT · −5]],
        [#text(size: 6.8pt, weight: 700, fill: accent)[PROPORTIONAL · q 0.85]],
        [],
        [#montserrat(
          clearance-lines.at(0),
          weight: style.chosen,
          italic: italic,
          size: 15pt,
          width: 86%,
          tracking: -5,
        )],
        [#proportional-line(
          clearance-lines.at(0),
          style,
          0.85,
          italic: italic,
          size: 15pt,
        )],
        [],
        [#montserrat(
          clearance-lines.at(1),
          weight: style.chosen,
          italic: italic,
          size: 15pt,
          width: 86%,
          tracking: -5,
        )],
        [#proportional-line(
          clearance-lines.at(1),
          style,
          0.85,
          italic: italic,
          size: 15pt,
        )],
      )
    ]
    #v(3mm)
  ]
]

#let spacing-groups = (
  (label: "control", sample: "asset dataset service"),
  (label: "h/r · g/h", sample: "through three shrink"),
  (label: "g/h words", sample: "high light weight"),
  (label: "stem pairs", sample: "minimum annual inline"),
  (label: "natural prose", sample: "language training inference"),
  (label: "diagonals", sample: "variable waveform layout"),
  (label: "acronyms", sample: "GPU API HTTP SNU EDGE"),
)

#let spacing-sample-cell(body, shade: false) = block(
  width: 100%,
  height: 15.5mm,
  inset: (x: 2mm, y: 2.2mm),
  fill: if shade { panel } else { white },
  stroke: 0.35pt + faint,
  radius: 1mm,
)[#body]

#for style in styles [
  #for italic in (false, true) [
    #let posture = if italic { "italic" } else { "upright" }
    #pagebreak()
    #proof-title(
      "06 · PROPORTIONAL SPACING",
      style.name + " · " + posture,
      note: "Compare the discarded additive −5 control with two global spacing scales. No word-specific pair correction is used.",
    )
    #grid(
      columns: (24mm, 1fr, 1fr, 1fr),
      gutter: 2mm,
      [#text(size: 7pt, weight: 700, fill: muted)[CONTEXT]],
      [#text(size: 7pt, weight: 700, fill: accent)[CURRENT · −5]],
      [#text(size: 7pt, weight: 700, fill: accent)[PROPORTIONAL · q 0.90]],
      [#text(size: 7pt, weight: 700, fill: accent)[PROPORTIONAL · q 0.85]],
    )
    #v(1.5mm)
    #for (index, group) in spacing-groups.enumerate() [
      #grid(
        columns: (24mm, 1fr, 1fr, 1fr),
        gutter: 2mm,
        align: (left, left, left, left),
        [#spacing-sample-cell(
          text(size: 6.8pt, weight: 650, fill: muted)[#group.label],
          shade: calc.rem(index, 2) == 0,
        )],
        [#spacing-sample-cell(
          montserrat(
            group.sample,
            weight: style.chosen,
            italic: italic,
            size: 11pt,
            width: 86%,
            tracking: -5,
          ),
          shade: calc.rem(index, 2) == 0,
        )],
        [#spacing-sample-cell(
          proportional-line(
            group.sample,
            style,
            0.90,
            italic: italic,
            size: 11pt,
          ),
          shade: calc.rem(index, 2) == 0,
        )],
        [#spacing-sample-cell(
          proportional-line(
            group.sample,
            style,
            0.85,
            italic: italic,
            size: 11pt,
          ),
          shade: calc.rem(index, 2) == 0,
        )],
      )
      #v(1.4mm)
    ]
    #text(size: 7pt, fill: muted)[Ligature and combining-mark behavior is intentionally excluded from these per-character simulations and must be checked in generated test fonts before packaging.]
  ]
]

#let pair-characters-lower = "abcdefghijklmnopqrstuvwxyz".clusters()
#let pair-characters-upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".clusters()

#let pair-matrix(
  style,
  characters,
  italic: false,
  spacing-scale: none,
) = {
  let header = (
    [],
    ..characters.map(character => [
      #align(center + horizon)[#text(size: 5.5pt, weight: 700, fill: muted)[#character]]
    ]),
  )
  let rows = characters.map(left => (
    [#align(center + horizon)[#text(size: 5.5pt, weight: 700, fill: muted)[#left]]],
    ..characters.map(right => [
      #align(center + horizon)[
        #if spacing-scale == none {
          montserrat(
            left + right,
            weight: style.chosen,
            italic: italic,
            size: 7pt,
            width: 86%,
            tracking: -5,
          )
        } else {
          proportional-word(
            left + right,
            style,
            spacing-scale,
            italic: italic,
            size: 7pt,
          )
        }
      ]
    ]),
  )).flatten()
  grid(
    columns: (1fr,) * (characters.len() + 1),
    rows: 5.35mm,
    column-gutter: 0.15mm,
    row-gutter: 0.15mm,
    ..header,
    ..rows,
  )
}

#for italic in (false, true) [
  #let posture = if italic { "italic" } else { "upright" }
  #for case-data in (
    (name: "lowercase", characters: pair-characters-lower),
    (name: "uppercase", characters: pair-characters-upper),
  ) [
    #for model in (
      (
        name: "current −5",
        spacing-scale: none,
        note: "Every row/column combination is rendered as one shaping run with native Montserrat kerning, 86% width, and current −5 tracking.",
      ),
      (
        name: "proportional q 0.85",
        spacing-scale: 0.85,
        note: "Every row/column combination uses the same proportional sidebearing and native-kerning rule; no pair-specific correction is present.",
      ),
    ) [
      #pagebreak()
      #proof-title(
        "07 · FULL PAIR MATRIX",
        "Regular " + posture + " · " + case-data.name + " · " + model.name,
        note: model.note,
      )
      #pair-matrix(
        styles.at(2),
        case-data.characters,
        italic: italic,
        spacing-scale: model.spacing-scale,
      )
    ]
  ]
]

// Raster H audit. The horizontal transform changes vertical stems but leaves
// the center crossbar's vertical thickness unchanged, so the two measurements
// expose Montserrat's changing H stroke contrast rather than conflating it with
// the selected 86% width.
#let one-decimal(value) = str(calc.round(value * 10) / 10)

#let h-weight-panel(style-record, italic: false) = {
  let record = if italic { style-record.italic } else { style-record }
  let posture = if italic { "true italic" } else { "upright" }
  block(
  width: 100%,
  inset: 2.5mm,
  fill: panel,
  stroke: 0.4pt + faint,
  radius: 1.5mm,
)[
  #text(size: 8.5pt, weight: 700)[#record.style · #posture · Edge nominal #record.edge_weight]
  #v(1.5mm)
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 1.5mm,
    align: (center, center, center),
    [
      #text(size: 6.5pt, weight: 700, fill: accent)[SNU EDGE v1 REFERENCE]
      #linebreak()
      #text(size: 5.8pt, fill: muted)[bar #one-decimal(record.edge.crossbar) · v-stem #one-decimal(record.edge.vertical_stem)]
    ],
    [
      #text(size: 6.5pt, weight: 700, fill: accent)[CURRENT · wght #record.current.weight]
      #linebreak()
      #text(size: 5.8pt, fill: muted)[bar #one-decimal(record.current.crossbar) · v\@86 #one-decimal(record.current.vertical_stem_at_86)]
    ],
    [
      #text(size: 6.5pt, weight: 700, fill: accent)[H-BAR MATCH · wght #record.match.weight]
      #linebreak()
      #text(size: 5.8pt, fill: muted)[bar #one-decimal(record.match.crossbar) · x(v) #one-decimal(record.match.vertical_match_width_scale * 100)%]
    ],
  )
  #v(1mm)
  #image(
    record.image,
    width: 100%,
  )
]
}

#for italic in (false, true) [
  #for records in (
    h-weight-audit.styles.slice(0, 2),
    h-weight-audit.styles.slice(2, 4),
    h-weight-audit.styles.slice(4, 6),
    h-weight-audit.styles.slice(6, 8),
  ) [
    #pagebreak()
    #proof-title(
      "08 · RASTER H WEIGHT MATCH",
      "Crossbar thickness at large raster size",
      note: "All H glyphs are unhinted rasterizations at the same em size. Montserrat is compressed to 86% width; red brackets mark the crossbar. x(v) is the horizontal scale that would separately match the H vertical stem.",
    )
    #grid(
      columns: (1fr, 1fr),
      gutter: 4mm,
      row-gutter: 4mm,
      ..records.map(record => h-weight-panel(record, italic: italic)),
    )
  ]
]
