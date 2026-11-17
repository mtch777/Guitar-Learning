const keys = [
  { label: "C", accidental: "0", color: "#34A853" },
  { label: "G", accidental: "♯", color: "#7CB342" },
  { label: "D", accidental: "♯♯", color: "#C0CA33" },
  { label: "A", accidental: "♯♯♯", color: "#FDD835" },
  { label: "E", accidental: "♯♯♯♯", color: "#FFB300" },
  { label: "B", accidental: "♯♯♯♯♯", color: "#FB8C00" },
  { label: "F♯ / G♭", accidental: "♯♯♯♯♯♯ / ♭♭♭♭♭♭", color: "#EA4335" },
  { label: "D♭", accidental: "♭♭♭♭♭", color: "#7E57C2" },
  { label: "A♭", accidental: "♭♭♭♭", color: "#5C6BC0" },
  { label: "E♭", accidental: "♭♭♭", color: "#42A5F5" },
  { label: "B♭", accidental: "♭♭", color: "#26A69A" },
  { label: "F", accidental: "♭", color: "#5BBE7A" }
];

const svg = document.getElementById("circleSvg");
const CX = 320, CY = 320, OUTER_R = 270, INNER_R = 150;
const ANGLE_PER = 360 / keys.length;

function polar(radius, angleDeg) {
  const r = ((angleDeg - 90) * Math.PI) / 180;
  return { x: CX + radius * Math.cos(r), y: CY + radius * Math.sin(r) };
}

function slicePath(startAngle, endAngle) {
  const a = polar(OUTER_R, startAngle);
  const b = polar(OUTER_R, endAngle);
  const c = polar(INNER_R, endAngle);
  const d = polar(INNER_R, startAngle);
  return [
    "M", a.x, a.y,
    "A", OUTER_R, OUTER_R, 0, 0, 1, b.x, b.y,
    "L", c.x, c.y,
    "A", INNER_R, INNER_R, 0, 0, 0, d.x, d.y,
    "Z"
  ].join(" ");
}

function node(tag, attrs, text) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs || {}).forEach(([k,v]) => el.setAttribute(k,v));
  if (text !== undefined) el.textContent = text;
  return el;
}

keys.forEach((key, i) => {
  const angle = i * ANGLE_PER;
  svg.appendChild(node("path", {
    d: slicePath(angle - ANGLE_PER/2, angle + ANGLE_PER/2),
    fill: key.color,
    class: "wedge"
  }));

  const keyPoint = polar(215, angle);
  const accPoint = polar(178, angle);

  svg.appendChild(node("text", {
    x: keyPoint.x, y: keyPoint.y, class: "key-name",
    "font-size": key.label.length > 4 ? 19 : 25
  }, key.label));

  svg.appendChild(node("text", {
    x: accPoint.x, y: accPoint.y, class: "accidental-count",
    "font-size": key.accidental.length > 5 ? 13 : 16
  }, key.accidental));
});

svg.appendChild(node("circle", {
  cx: CX, cy: CY, r: INNER_R - 8, class: "center-disc"
}));
svg.appendChild(node("text", {
  x: CX, y: CY - 5, class: "center-title"
}, "Circle of Fifths"));
svg.appendChild(node("text", {
  x: CX, y: CY + 28, class: "accidental-count"
}, "Major keys"));