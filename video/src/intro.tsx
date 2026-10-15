import React from "react";
import { AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Bg, H, Kicker, M, P, Pop, Slam } from "./ui";
import { C, display, mono, s } from "./theme";

const ALERTS = [
  "ci-deploy token found in public build log",
  "AssumeRole ci-deploy → deployer",
  "deployer ADMIN_TO prod-customers-db",
  "deployer READS billing-secrets",
  "ci-deploy MEMBER_OF platform-ci",
  "platform-ci CAN_ASSUME db-maint",
  "db-maint READS prod-customers-db",
  "unusual API volume: ci-deploy",
  "new session from unknown ASN",
  "token age: 412 days",
  "secret scanner: 1 match",
  "who owns ci-deploy?",
];

/** 0–6 s: an alert storm nobody can act on. */
export const ColdOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const freeze = s(3.5);
  const f = Math.min(frame, freeze);
  const count = Math.min(40, Math.floor(interpolate(f, [0, freeze], [1, 40])));
  const shake = frame < freeze ? (random(`sh${frame}`) - 0.5) * 8 : 0;
  const dim = interpolate(frame, [freeze, freeze + 10], [1, 0.14], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Bg />
      <AbsoluteFill style={{ opacity: dim, transform: `translate(${shake}px, ${-shake / 2}px)` }}>
        {Array.from({ length: 44 }).map((_, i) => {
          const born = i * 2.2;
          if (f < born) return null;
          const col = i % 3;
          const x = 70 + col * 600 + random(`x${i}`) * 60;
          const y = 1080 - (f - born) * 10 - random(`y${i}`) * 60;
          const p = Math.min(1, (f - born) / 5);
          const sev = random(`v${i}`);
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x,
                top: y,
                opacity: p,
                transform: `scale(${0.7 + p * 0.3})`,
                display: "flex",
                gap: 14,
                alignItems: "center",
                fontFamily: mono,
                fontSize: 21,
                color: C.text,
                background: "#141826",
                border: `1.5px solid ${C.line}`,
                borderLeft: `5px solid ${sev > 0.6 ? C.jewel : sev > 0.3 ? C.warn : C.muted}`,
                padding: "11px 18px",
                borderRadius: 10,
                whiteSpace: "nowrap",
              }}
            >
              <span style={{ color: sev > 0.6 ? C.jewel : C.warn, fontWeight: 700 }}>{sev > 0.6 ? "CRIT" : "HIGH"}</span>
              {ALERTS[i % ALERTS.length]}
            </div>
          );
        })}
        <div style={{ position: "absolute", right: 70, top: 50, fontFamily: mono, fontWeight: 700, fontSize: 40, color: "#fff", background: C.jewel, borderRadius: 999, padding: "10px 26px" }}>
          {count === 40 ? "40+" : count} alerts
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 14 }}>
        <Slam at={3.6} size={140}>1 leaked token.</Slam>
        <Slam at={4.3} size={110} color={C.accent}>
          What do you cut?
        </Slam>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** 6–10.5 s: a graph collapses onto one dashed cut → Chokepoint. */
export const Logo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const cut = spring({ frame: frame - 6, fps, config: { damping: 14 } });
  const word = "Chokepoint".split("");
  const nodes = Array.from({ length: 14 }).map((_, i) => ({ a: (i / 14) * Math.PI * 2, r: 300 + random(`r${i}`) * 260 }));
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <Bg />
      {nodes.map((n, i) => {
        const p = spring({ frame: frame - i, fps, config: { damping: 16 } });
        const r = interpolate(p, [0, 1], [n.r * 1.8, n.r]);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: 960 + Math.cos(n.a) * r * 1.4 - 9,
              top: 540 + Math.sin(n.a) * r * 0.75 - 9,
              width: 18,
              height: 18,
              borderRadius: i % 4 === 0 ? 3 : "50%",
              background: i % 4 === 0 ? C.jewel : C.muted,
              opacity: 0.35 * p,
            }}
          />
        );
      })}
      <div style={{ display: "flex", alignItems: "center", gap: 30 }}>
        <svg width={120} height={120} viewBox="0 0 120 120" style={{ transform: `rotate(${interpolate(cut, [0, 1], [-90, 0])}deg)`, opacity: cut }}>
          <circle cx={20} cy={60} r={12} fill={C.text} />
          <rect x={88} y={48} width={24} height={24} fill={C.jewel} />
          <line x1={32} y1={60} x2={88} y2={60} stroke={C.muted} strokeWidth={6} />
          <line x1={60} y1={18} x2={60} y2={102} stroke={C.accent} strokeWidth={8} strokeDasharray="12 9" strokeLinecap="round" />
        </svg>
        <div style={{ display: "flex" }}>
          {word.map((ch, i) => {
            const p = spring({ frame: frame - 10 - i * 2, fps, config: { damping: 12 } });
            return (
              <span
                key={i}
                style={{
                  fontFamily: display,
                  fontWeight: 800,
                  fontSize: 180,
                  letterSpacing: "-0.04em",
                  color: C.text,
                  opacity: p,
                  transform: `translateY(${interpolate(p, [0, 1], [80, 0])}px)`,
                  display: "inline-block",
                }}
              >
                {ch}
              </span>
            );
          })}
        </div>
      </div>
      <div style={{ position: "absolute", top: 720 }}>
        <Pop at={1.4}>
          <P size={38} style={{ color: C.text, textAlign: "center" }}>
            The <b style={{ color: C.accent }}>cheapest cut</b> that's <b style={{ color: C.accent }}>safe to ship</b>, proven on a FalkorDB graph
          </P>
        </Pop>
      </div>
    </AbsoluteFill>
  );
};

const OPTIONS = [
  { title: "Revoke everything", cost: "cost 19", note: "Revoke everything the token's identity holds. Whatever depended on it breaks.", col: C.muted, bad: true },
  { title: "Cheapest cut", cost: "cost 5", note: "Cuts G-102, the grant DR failover runs on. Next outage: no failover.", col: C.warn, bad: true },
  { title: "Chokepoint", cost: "cost 6", note: "Attacker cut off. DR failover still works. Proven, cited.", col: C.accent, bad: false },
];

/** 10.5–19.5 s: the trade-off, with the real numbers from finding F-1. */
export const Problem: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Bg />
      <div style={{ position: "absolute", left: 130, top: 120, right: 130 }}>
        <Kicker>Finding F-1 · ci-deploy token leaked</Kicker>
        <H size={68} style={{ marginTop: 16 }}>
          Cut the attacker off, <span style={{ color: C.accent }}>not the company.</span>
        </H>
      </div>
      <div style={{ position: "absolute", left: 130, right: 130, top: 420, display: "flex", gap: 40 }}>
        {OPTIONS.map((o, i) => {
          const p = spring({ frame: frame - s(0.8 + i * 1.6), fps: 30, config: { damping: 13 } });
          const strike = spring({ frame: frame - s(1.9 + i * 1.6), fps: 30, config: { damping: 16 } });
          return (
            <div
              key={o.title}
              style={{
                flex: 1,
                opacity: p,
                transform: `translateY(${(1 - p) * 60}px) scale(${o.bad ? 1 : interpolate(strike, [0, 1], [1, 1.05])})`,
                background: o.bad ? C.panel : "#16204a",
                border: `2px solid ${o.bad ? C.line : C.accent}`,
                borderRadius: 24,
                padding: "34px 34px 38px",
                position: "relative",
                boxShadow: o.bad ? "none" : `0 0 ${60 * strike}px rgba(91,124,255,0.35)`,
              }}
            >
              <div style={{ fontFamily: mono, fontSize: 22, color: o.col, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase" }}>{o.title}</div>
              <div style={{ fontFamily: display, fontWeight: 800, fontSize: 96, color: C.text, letterSpacing: "-0.04em", marginTop: 8 }}>{o.cost}</div>
              <div style={{ fontFamily: display, fontSize: 28, color: C.muted, marginTop: 10, lineHeight: 1.3 }}>{o.note}</div>
              <div
                style={{
                  position: "absolute",
                  right: 26,
                  top: 26,
                  fontFamily: display,
                  fontWeight: 800,
                  fontSize: 54,
                  color: o.bad ? C.jewel : C.green,
                  opacity: strike,
                  transform: `scale(${interpolate(strike, [0, 1], [2, 1])})`,
                }}
              >
                {o.bad ? "✗" : "✓"}
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 130, bottom: 110 }}>
        <Pop at={6.4}>
          <P size={28}>
            cost = 1 + ⌈log₂(1 + uses in 30 days)⌉ per grant: <M color={C.text}>cheap to cut = nobody uses it</M>
          </P>
        </Pop>
      </div>
    </AbsoluteFill>
  );
};

const TRACKS = [
  { n: "01", name: "Agent that acts", what: "Gemini calls graph algorithms as tools: maxFlow, BFS, shortest path. Also served over MCP." },
  { n: "02", name: "Memory", what: "Risk decisions live in the graph and re-check themselves when the graph changes." },
  { n: "03", name: "Company brain", what: "Tickets, people, chat and policy linked to the exact grant they explain." },
];

/** 19.5–26 s: one app, three tracks, one graph. */
export const Tracks: React.FC = () => {
  const frame = useCurrentFrame();
  const core = spring({ frame: frame - s(2.6), fps: 30, config: { damping: 14 } });
  return (
    <AbsoluteFill>
      <Bg />
      <div style={{ position: "absolute", left: 130, top: 110 }}>
        <Kicker>Graph Hacks · all three tracks</Kicker>
        <H size={68} style={{ marginTop: 14 }}>
          One app. <span style={{ color: C.accent }}>One graph.</span>
        </H>
      </div>
      <div style={{ position: "absolute", left: 130, right: 130, top: 360, display: "flex", gap: 34 }}>
        {TRACKS.map((t, i) => {
          const p = spring({ frame: frame - s(0.5 + i * 0.6), fps: 30, config: { damping: 13 } });
          return (
            <div key={t.n} style={{ flex: 1, opacity: p, transform: `translateY(${(1 - p) * 50}px)`, background: C.panel, border: `1.5px solid ${C.line}`, borderRadius: 22, padding: "30px 32px" }}>
              <div style={{ fontFamily: mono, fontSize: 22, color: C.accent, fontWeight: 700 }}>TRACK {t.n}</div>
              <div style={{ fontFamily: display, fontWeight: 800, fontSize: 46, color: C.text, marginTop: 8 }}>{t.name}</div>
              <div style={{ fontFamily: display, fontSize: 26, color: C.muted, marginTop: 12, lineHeight: 1.3 }}>{t.what}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 790, display: "flex", justifyContent: "center", opacity: core, transform: `scale(${interpolate(core, [0, 1], [0.8, 1])})` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18, fontFamily: display, fontWeight: 800, fontSize: 40, color: C.text, background: "#16204a", border: `2px solid ${C.accent}`, borderRadius: 18, padding: "18px 34px" }}>
          <span style={{ color: C.accent }}>●</span> FalkorDB · 888 nodes · 958 attack edges · 1,461 context edges
        </div>
      </div>
    </AbsoluteFill>
  );
};
