const keys = [
  { label: "C", color: "#34A853" },
  { label: "G", color: "#7CB342" },
  { label: "D", color: "#C0CA33" },
  { label: "A", color: "#FDD835" },
  { label: "E", color: "#FFB300" },
  { label: "B", color: "#FB8C00" },
  { label: "F#/Gb", color: "#EA4335" },
  { label: "Db", color: "#7E57C2" },
  { label: "Ab", color: "#5C6BC0" },
  { label: "Eb", color: "#42A5F5" },
  { label: "Bb", color: "#26A69A" },
  { label: "F", color: "#5BBE7A" }
];

const svg = document.getElementById("circleSvg");

const SIZE = 600;
const CX = SIZE / 2;
const CY = SIZE / 2;
const OUTER_R = 250;
const INNER_R = 145;
const ANGLE_PER = 360 / keys.length;

function polarToCartesian(cx, cy, radius, angleDeg) {
  const radians = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(radians),
    y: cy + radius * Math.sin(radians)
  };
}

function ringSlicePath(cx, cy, outerR, innerR, startAngle, endAngle) {
  const outerStart = polarToCartesian(cx, cy, outerR, startAngle);
  const outerEnd = polarToCartesian(cx, cy, outerR, endAngle);
  const innerEnd = polarToCartesian(cx, cy, innerR, endAngle);
  const innerStart = polarToCartesian(cx, cy, innerR, startAngle);

  return [
    "M " + outerStart.x + " " + outerStart.y,
    "A " + outerR + " " + outerR + " 0 0 1 " + outerEnd.x + " " + outerEnd.y,
    "L " + innerEnd.x + " " + innerEnd.y,
    "A " + innerR + " " + innerR + " 0 0 0 " + innerStart.x + " " + innerStart.y,
    "Z"
  ].join(" ");
}

function makeSvg(tag, attrs) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tag);

  Object.entries(attrs || {}).forEach(([key, value]) => {
    node.setAttribute(key, value);
  });

  return node;
}

keys.forEach((key, index) => {
  const centerAngle = index * ANGLE_PER;
  const startAngle = centerAngle - ANGLE_PER / 2;
  const endAngle = centerAngle + ANGLE_PER / 2;

  const path = makeSvg("path", {
    d: ringSlicePath(
      CX,
      CY,
      OUTER_R,
      INNER_R,
      startAngle,
      endAngle
    ),
    fill: key.color,
    class: "wedge"
  });

  svg.appendChild(path);

  const labelPoint = polarToCartesian(
    CX,
    CY,
    (OUTER_R + INNER_R) / 2,
    centerAngle
  );

  const text = makeSvg("text", {
    x: labelPoint.x,
    y: labelPoint.y,
    class: "key-label",
    "font-size": key.label === "F#/Gb" ? 17 : 23
  });

  text.textContent = key.label;
  svg.appendChild(text);
});

const center = makeSvg("circle", {
  cx: CX,
  cy: CY,
  r: INNER_R - 8,
  class: "center-disc"
});

svg.appendChild(center);