import React from "react";
import { AbsoluteFill } from "remotion";
import { C, display, mono } from "./theme";

/** README hero banner 1600×560. The mini graph is F-1's real attack graph with the agent's cut (G-101, G-106). */
const N = {
  f: { x: 70, y: 250 },
  tok: { x: 175, y: 250 },
  ci: { x: 280, y: 250 },
  dep: { x: 430, y: 150 },
  pci: { x: 380, y: 370 },
  dbm: { x: 530, y: 370 },
  prod: { x: 640, y: 250 },
  bill: { x: 610, y: 70 },
};
const E: [keyof typeof N, keyof typeof N, string?][] = [
  ["f", "tok"], ["tok", "ci"], ["ci", "dep", "cut"], ["ci", "pci"], ["pci", "dbm", "cut"],
  ["dep", "prod", "kept"], ["dep", "bill"], ["dbm", "prod"],
];

export const Banner: React.FC = () => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(rgba(147,168,255,0.08) 1.5px, transparent 1.6px) 0 0 / 34px 34px,
        radial-gradient(circle at 80% 45%, #1a2560 0%, ${C.bg} 60%)`,
    }}
  >
    <div style={{ position: "absolute", left: 80, top: 86, width: 960 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
        <svg width={92} height={92} viewBox="0 0 120 120">
          <circle cx={20} cy={60} r={12} fill={C.text} />
          <rect x={88} y={48} width={24} height={24} fill={C.jewel} />
          <line x1={32} y1={60} x2={88} y2={60} stroke={C.muted} strokeWidth={6} />
          <line x1={60} y1={18} x2={60} y2={102} stroke={C.accent} strokeWidth={8} strokeDasharray="12 9" strokeLinecap="round" />
        </svg>
        <div style={{ fontFamily: display, fontWeight: 800, fontSize: 120, letterSpacing: "-0.045em", color: C.text, lineHeight: 1 }}>Chokepoint</div>
      </div>
      <div style={{ fontFamily: display, fontWeight: 600, fontSize: 38, color: C.text, marginTop: 30, lineHeight: 1.2 }}>
        The <span style={{ color: C.accent }}>cheapest access cut</span> that's <span style={{ color: C.accent }}>safe to ship</span>,
        <br />
        proven on a FalkorDB graph.
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 36 }}>
        {["01 · Agent that acts", "02 · Memory", "03 · Company brain"].map((t) => (
          <div key={t} style={{ fontFamily: mono, fontWeight: 700, fontSize: 21, color: C.text, background: C.panel, border: `1.5px solid ${C.line}`, borderRadius: 12, padding: "10px 16px" }}>
            {t}
          </div>
        ))}
      </div>
    </div>
    <svg width={720} height={460} style={{ position: "absolute", right: 50, top: 60 }}>
      {E.map(([a, b, k]) => (
        <line
          key={`${a}${b}`}
          x1={N[a].x}
          y1={N[a].y}
          x2={N[b].x}
          y2={N[b].y}
          stroke={k === "cut" ? C.accent : k === "kept" ? C.warn : "#3a4256"}
          strokeWidth={k ? 5 : 3}
          strokeDasharray={k === "cut" ? "12 9" : undefined}
        />
      ))}
      <text x={262} y={178} fontFamily={mono} fontSize={18} fontWeight={700} fill={C.accent}>✂ G-101</text>
      <text x={420} y={405} fontFamily={mono} fontSize={18} fontWeight={700} fill={C.accent}>✂ G-106</text>
      <text x={520} y={185} fontFamily={mono} fontSize={18} fontWeight={700} fill={C.warn}>G-102 kept (DR)</text>
      {Object.entries(N).map(([id, p]) =>
        id === "prod" || id === "bill" ? (
          <rect key={id} x={p.x - 18} y={p.y - 18} width={36} height={36} fill={C.jewel} />
        ) : id === "f" ? (
          <rect key={id} x={p.x - 15} y={p.y - 15} width={30} height={30} fill={C.text} transform={`rotate(45 ${p.x} ${p.y})`} />
        ) : (
          <circle key={id} cx={p.x} cy={p.y} r={14} fill={C.text} />
        ),
      )}
      <rect x={430} y={430} width={250} height={30} rx={8} fill={C.green} />
      <text x={555} y={451} textAnchor="middle" fontFamily={mono} fontSize={17} fontWeight={700} fill={C.bg}>
        ✓ algo.maxFlow = 0
      </text>
    </svg>
  </AbsoluteFill>
);
