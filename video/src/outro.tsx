import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame } from "remotion";
import { Bg, Chip, Code, H, Kicker, P, Pop, Slam } from "./ui";
import { C, display, END_URL, mono, s } from "./theme";

/* F-1's real attack graph (same nodes and grant ids as the app). */
type N = { id: string; x: number; y: number; kind?: "finding" | "jewel" };
const NODES: N[] = [
  { id: "F-1", x: 110, y: 610, kind: "finding" },
  { id: "ci-deploy-token", x: 270, y: 610 },
  { id: "ci-deploy", x: 440, y: 610 },
  { id: "deployer", x: 700, y: 430 },
  { id: "platform-ci", x: 610, y: 800 },
  { id: "db-maint", x: 880, y: 800 },
  { id: "prod-customers-db", x: 1060, y: 610, kind: "jewel" },
  { id: "billing-secrets", x: 1030, y: 300, kind: "jewel" },
];
const P_ = (id: string) => NODES.find((n) => n.id === id)!;
const EDGES = [
  { a: "F-1", b: "ci-deploy-token" },
  { a: "ci-deploy-token", b: "ci-deploy" },
  { a: "ci-deploy", b: "deployer", g: "G-101" },
  { a: "ci-deploy", b: "platform-ci", g: "G-105" },
  { a: "platform-ci", b: "db-maint", g: "G-106" },
  { a: "deployer", b: "prod-customers-db", g: "G-102" },
  { a: "deployer", b: "billing-secrets", g: "G-103" },
  { a: "db-maint", b: "prod-customers-db", g: "G-107" },
];
const ROUTES = [
  ["F-1", "ci-deploy-token", "ci-deploy", "deployer", "prod-customers-db"],
  ["F-1", "ci-deploy-token", "ci-deploy", "deployer", "billing-secrets"],
  ["F-1", "ci-deploy-token", "ci-deploy", "platform-ci", "db-maint", "prod-customers-db"],
];
const P0 = ["G-102", "G-103", "G-106"];
const P1 = ["G-101", "G-106"];

const along = (route: string[], u: number) => {
  const pts = route.map(P_);
  const seg = pts.slice(1).map((p, i) => Math.hypot(p.x - pts[i].x, p.y - pts[i].y));
  let d = u * seg.reduce((a, b) => a + b, 0);
  for (let i = 0; i < seg.length; i++) {
    if (d <= seg[i]) return { x: pts[i].x + ((pts[i + 1].x - pts[i].x) * d) / seg[i], y: pts[i].y + ((pts[i + 1].y - pts[i].y) * d) / seg[i], i };
    d -= seg[i];
  }
  const last = pts[pts.length - 1];
  return { x: last.x, y: last.y, i: seg.length - 1 };
};

/** "The LLM proposes, the graph disposes": min-cut, what_if, verify. */
export const MinCut: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const phase = t < 3.6 ? 0 : t < 6.8 ? 1 : 2; // flow → P0 → P1 + verify
  const cutSet = phase === 1 ? P0 : phase === 2 ? P1 : [];
  const cutP = spring({ frame: frame - s(phase === 1 ? 3.6 : 6.8), fps: 30, config: { damping: 14 } });
  const zero = spring({ frame: frame - s(9.0), fps: 30, config: { damping: 12 } });
  return (
    <AbsoluteFill>
      <Bg />
      <div style={{ position: "absolute", left: 110, top: 80, width: 1100 }}>
        <Kicker>Under the hood · FalkorDB algorithms</Kicker>
        <H size={60} style={{ marginTop: 12 }}>
          The model proposes. <span style={{ color: C.accent }}>The graph disposes.</span>
        </H>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {EDGES.map((e) => {
          const a = P_(e.a);
          const b = P_(e.b);
          const isCut = e.g && cutSet.includes(e.g);
          const kept = phase === 2 && e.g === "G-102";
          const drDanger = phase === 1 && e.g === "G-102";
          const col = isCut ? (phase === 1 ? C.warn : C.accent) : kept ? C.warn : "#3a4256";
          return (
            <g key={`${e.a}-${e.b}`}>
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={col}
                strokeWidth={isCut || kept ? 5 : 3}
                strokeDasharray={isCut ? "14 10" : undefined}
                opacity={isCut ? interpolate(cutP, [0, 1], [0.3, 1]) : 1}
              />
              {e.g ? (
                <text
                  x={a.x + (b.x - a.x) * 0.56}
                  y={a.y + (b.y - a.y) * 0.56 - 16}
                  textAnchor="middle"
                  fontFamily={mono}
                  fontSize={20}
                  fontWeight={700}
                  fill={isCut ? col : kept ? C.warn : C.muted}
                >
                  {isCut ? "✂ " : ""}
                  {e.g}
                  {kept ? " · kept (cap ∞)" : drDanger ? " · DR needs it!" : ""}
                </text>
              ) : null}
            </g>
          );
        })}
        {ROUTES.map((r, ri) =>
          Array.from({ length: 4 }).map((_, k) => {
            const u = ((t * 0.32 + k / 4 + ri * 0.13) % 1) as number;
            const pos = along(r, u);
            // after the final cut, flow stops at the first cut edge on the route
            const blockedAt = phase === 2 ? r.findIndex((id, i) => i > 0 && EDGES.some((e) => e.a === r[i - 1] && e.b === id && e.g && P1.includes(e.g))) - 1 : 99;
            if (phase === 2 && pos.i >= blockedAt) return null;
            return <circle key={`${ri}-${k}`} cx={pos.x} cy={pos.y} r={7} fill={C.jewel} opacity={phase === 2 ? 1 - zero : 0.9} />;
          }),
        )}
        {NODES.map((n) =>
          n.kind === "jewel" ? (
            <rect key={n.id} x={n.x - 22} y={n.y - 22} width={44} height={44} fill={C.jewel} />
          ) : n.kind === "finding" ? (
            <rect key={n.id} x={n.x - 18} y={n.y - 18} width={36} height={36} fill={C.text} transform={`rotate(45 ${n.x} ${n.y})`} />
          ) : (
            <circle key={n.id} cx={n.x} cy={n.y} r={18} fill={C.text} />
          ),
        )}
        {NODES.map((n) => (
          <text key={`l${n.id}`} x={n.x} y={n.y + 48} textAnchor="middle" fontFamily={display} fontSize={22} fontWeight={600} fill={C.text}>
            {n.id}
          </text>
        ))}
      </svg>
      <div style={{ position: "absolute", left: 110, top: 900, display: "flex", gap: 16 }}>
        {phase >= 1 ? (
          <Chip size={24} color={phase === 1 ? C.bg : C.text} bg={phase === 1 ? C.warn : C.panel} style={{ border: "none" }}>
            P0 · min cut · cost 5{phase === 2 ? " ✗ breaks DR" : ""}
          </Chip>
        ) : (
          <Chip size={24}>3 routes to 2 crown jewels</Chip>
        )}
        {phase === 2 ? (
          <Chip size={24} color="#fff" bg={C.accent} style={{ border: "none", opacity: cutP }}>
            P1 · keep G-102 · cost 6
          </Chip>
        ) : null}
        <div style={{ opacity: zero, transformOrigin: "left center", transform: `scale(${interpolate(zero, [0, 1], [1.6, 1])})` }}>
          <Chip size={24} color={C.bg} bg={C.green} style={{ border: "none" }}>
            ✓ verify: maxFlow = 0
          </Chip>
        </div>
      </div>
      <div style={{ position: "absolute", left: 1190, top: 300, width: 680 }}>
        <Code
          at={0.6}
          step={0.75}
          size={19}
          lines={[
            { t: "// grants are nodes; every move is one :ATTACK edge", c: C.muted },
            { t: "CALL algo.maxFlow({sourceNodes: [f]," },
            { t: "  targetNodes: jewels, capacityProperty: 'cf'})" },
            { t: "// cut = saturated edges of the residual graph", c: C.muted },
            { t: "// unique? source-side cut == sink-side cut", c: C.muted },
            { t: "what_if(keep G-102) → cf = ∞ → P1, cost 6", c: C.accentSoft },
            { t: "verify: remove the cut, maxFlow again → 0 ✓", c: C.green },
          ]}
        />
        <Pop at={7.2}>
          <P size={24} style={{ marginTop: 22 }}>
            The model never computes a cut. It asks. Every plan it picks is re-checked by FalkorDB before anyone sees it.
          </P>
        </Pop>
      </div>
    </AbsoluteFill>
  );
};

const STATS = [
  { n: 128, label: "automated tests on a real FalkorDB, no mocks", suffix: "" },
  { n: 6, label: "of 6 live Gemini runs kept DR safe*", suffix: "/6" },
  { n: 11, label: "graph tools, also served over MCP", suffix: "" },
  { n: 0, label: "decisions saved without a human", suffix: "" },
];

export const Stats: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Bg />
      <div style={{ position: "absolute", left: 150, top: 90 }}>
        <Kicker>Engineering, not a demo trick</Kicker>
        <H size={62} style={{ marginTop: 12 }}>Built to be trusted with access.</H>
      </div>
      <div style={{ position: "absolute", left: 150, top: 290, display: "grid", gridTemplateColumns: "1fr 1fr", columnGap: 90, rowGap: 40, width: 1620 }}>
        {STATS.map((st, i) => {
          const p = spring({ frame: frame - s(0.5 + i * 0.5), fps: 30, config: { damping: 12 } });
          const val = Math.round(interpolate(p, [0, 1], [0, st.n]));
          return (
            <div key={st.label} style={{ display: "flex", alignItems: "baseline", gap: 26, opacity: Math.min(1, p * 1.5) }}>
              <div style={{ fontFamily: display, fontWeight: 800, fontSize: 110, color: i === 1 ? C.accent : C.text, minWidth: 250, letterSpacing: "-0.04em" }}>
                {val}
                {st.suffix}
              </div>
              <div style={{ fontFamily: display, fontSize: 32, color: C.muted, maxWidth: 470 }}>{st.label}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 150, bottom: 120, display: "flex", gap: 14, flexWrap: "wrap", width: 1620 }}>
        {[
          "Server re-verifies every plan",
          "Citation guard",
          "Prompt injection in the data: ignored",
          "Per-visitor graph copy (GRAPH.COPY)",
          "Read-only ad-hoc Cypher + TIMEOUT",
          "Runs on FalkorDB Cloud",
        ].map((t, i) => (
          <Pop key={t} at={2.8 + i * 0.25}>
            <Chip size={23}>{t}</Chip>
          </Pop>
        ))}
      </div>
      <div style={{ position: "absolute", left: 150, bottom: 60, fontFamily: mono, fontSize: 18, color: C.muted }}>
        * 2 Oct 2026, gemini-2.5-flash + gemini-3.5-flash on finding F-1; runs stopped by the free-tier quota fell back to the graph's plan and are not counted.
      </div>
    </AbsoluteFill>
  );
};

export const End: React.FC = () => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [s(6.6), s(8)], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: fade }}>
      <Bg />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 12 }}>
        <Slam at={0.2} size={130}>Find the cut.</Slam>
        <Slam at={0.7} size={130}>Prove it.</Slam>
        <Slam at={1.2} size={130} color={C.accent}>
          Remember why.
        </Slam>
        <Pop at={2.2}>
          <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 40 }}>
            <svg width={52} height={52} viewBox="0 0 120 120">
              <circle cx={20} cy={60} r={12} fill={C.text} />
              <rect x={88} y={48} width={24} height={24} fill={C.jewel} />
              <line x1={32} y1={60} x2={88} y2={60} stroke={C.muted} strokeWidth={6} />
              <line x1={60} y1={18} x2={60} y2={102} stroke={C.accent} strokeWidth={8} strokeDasharray="12 9" strokeLinecap="round" />
            </svg>
            <div style={{ fontFamily: display, fontWeight: 800, fontSize: 64, color: C.text }}>Chokepoint</div>
          </div>
        </Pop>
        <Pop at={2.7}>
          <P size={30} style={{ color: C.text, textAlign: "center" }}>
            Harsh Patil · Graph Hacks 2026 · FalkorDB + Gemini
          </P>
        </Pop>
        <Pop at={3.1}>
          <div style={{ fontFamily: mono, fontSize: 30, color: C.accentSoft, marginTop: 8 }}>{END_URL}</div>
        </Pop>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
