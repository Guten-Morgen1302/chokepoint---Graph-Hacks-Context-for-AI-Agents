import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { C, display, mono, s } from "./theme";

/** Spring-in from frame `at` (seconds, relative to the current Sequence). */
export const useIn = (at: number, damping = 14) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - s(at), fps, config: { damping, stiffness: 140, mass: 0.7 } });
};

export const Pop: React.FC<{ at: number; children: React.ReactNode; from?: "up" | "left" | "scale"; style?: React.CSSProperties }> = ({
  at,
  children,
  from = "up",
  style,
}) => {
  const p = useIn(at);
  const t =
    from === "left"
      ? `translateX(${interpolate(p, [0, 1], [-60, 0])}px)`
      : from === "scale"
        ? `scale(${interpolate(p, [0, 1], [0.6, 1])})`
        : `translateY(${interpolate(p, [0, 1], [40, 0])}px)`;
  return <div style={{ opacity: Math.min(1, p * 1.4), transform: t, ...style }}>{children}</div>;
};

/** Slams in big then settles: for the punchy lines. */
export const Slam: React.FC<{ at: number; children: React.ReactNode; size?: number; color?: string; style?: React.CSSProperties }> = ({
  at,
  children,
  size = 120,
  color = C.text,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - s(at), fps, config: { damping: 11, stiffness: 220, mass: 0.6 } });
  const scale = interpolate(p, [0, 1], [2.4, 1]);
  return (
    <div
      style={{
        fontFamily: display,
        fontWeight: 800,
        fontSize: size,
        lineHeight: 0.95,
        letterSpacing: "-0.03em",
        color,
        opacity: p > 0.01 ? 1 : 0,
        transform: `scale(${scale})`,
        filter: `blur(${interpolate(p, [0, 0.6, 1], [14, 2, 0])}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** Dark gradient with a faint dot grid: the graph is the backdrop. */
export const Bg: React.FC = () => {
  const frame = useCurrentFrame();
  const a = interpolate(frame % 600, [0, 600], [0, 360]);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(rgba(147,168,255,0.07) 1.5px, transparent 1.6px) 0 ${(frame * 0.3) % 36}px / 36px 36px,
          linear-gradient(${135 + Math.sin((a * Math.PI) / 180) * 8}deg, ${C.bg} 0%, ${C.bg2} 55%, ${C.bg} 100%)`,
      }}
    />
  );
};

export const Kicker: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = C.accent }) => (
  <div style={{ fontFamily: mono, fontSize: 21, letterSpacing: "0.14em", textTransform: "uppercase", color, fontWeight: 700 }}>
    {children}
  </div>
);

export const H: React.FC<{ children: React.ReactNode; size?: number; style?: React.CSSProperties }> = ({ children, size = 64, style }) => (
  <div style={{ fontFamily: display, fontWeight: 800, fontSize: size, lineHeight: 1.02, letterSpacing: "-0.025em", color: C.text, ...style }}>
    {children}
  </div>
);

export const P: React.FC<{ children: React.ReactNode; size?: number; style?: React.CSSProperties }> = ({ children, size = 30, style }) => (
  <div style={{ fontFamily: display, fontWeight: 400, fontSize: size, lineHeight: 1.3, color: C.muted, ...style }}>{children}</div>
);

export const M: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color }) => (
  <span style={{ fontFamily: mono, fontSize: "0.86em", color }}>{children}</span>
);

export const Chip: React.FC<{ children: React.ReactNode; color?: string; bg?: string; size?: number; style?: React.CSSProperties }> = ({
  children,
  color = C.text,
  bg = C.panel,
  size = 26,
  style,
}) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 12,
      padding: "12px 20px",
      borderRadius: 14,
      background: bg,
      border: `1.5px solid ${C.line}`,
      fontFamily: display,
      fontWeight: 600,
      fontSize: size,
      lineHeight: 1.2,
      color,
      ...style,
    }}
  >
    {children}
  </div>
);

export const Code: React.FC<{ lines: { t: string; c?: string }[]; at: number; step?: number; size?: number }> = ({ lines, at, step = 0.35, size = 24 }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        fontFamily: mono,
        fontSize: size,
        lineHeight: 1.55,
        background: "#0c0f18",
        border: `1.5px solid ${C.line}`,
        borderRadius: 18,
        padding: "22px 26px",
        color: C.text,
        whiteSpace: "pre",
      }}
    >
      {lines.map((l, i) => {
        const start = s(at + i * step);
        const n = Math.max(0, Math.min(l.t.length, Math.floor((frame - start) * 2.6)));
        return (
          <div key={i} style={{ color: l.c ?? C.text, minHeight: size * 1.55 }}>
            {l.t.slice(0, n)}
            {n > 0 && n < l.t.length ? <span style={{ color: C.accent }}>▍</span> : null}
          </div>
        );
      })}
    </div>
  );
};

export const ease = Easing.bezier(0.16, 1, 0.3, 1);

/* ── footage ────────────────────────────────────────────────────────────── */

const SRC_W = 1440; // the recording's viewport
const SRC_H = 900;
export const WIN_W = 1180; // browser content box on the 1920×1080 canvas
export const WIN_H = (WIN_W * SRC_H) / SRC_W;
const BAR = 46;

/** Camera keyframe: at clip second `t`, centre source point (x, y) at zoom `z` (1 = whole page). */
export type Cam = { t: number; x: number; y: number; z: number };
/** A ring + label pinned to a rectangle of the recording (source px), visible from..to (clip seconds). */
export type Callout = { from: number; to: number; x: number; y: number; w: number; h: number; label?: string; color?: string; below?: boolean };

const camAt = (cams: Cam[], t: number) => {
  if (!cams.length) return { x: SRC_W / 2, y: SRC_H / 2, z: 1 };
  const k = cams.findIndex((c) => c.t > t);
  if (k === -1) return cams[cams.length - 1];
  if (k === 0) return cams[0];
  const a = cams[k - 1];
  const b = cams[k];
  const dur = Math.min(1.1, b.t - a.t);
  const u = ease(Math.min(1, Math.max(0, (t - (b.t - dur)) / dur)));
  return { x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u, z: a.z + (b.z - a.z) * u };
};

/** The real screen recording inside a browser window, with a slow camera and callouts. */
export const Browser: React.FC<{ src: string; cams?: Cam[]; callouts?: Callout[] }> = ({ src, cams = [], callouts = [] }) => {
  const frame = useCurrentFrame();
  const t = frame / 30;
  const cam = camAt(cams, t);
  const k = (WIN_W / SRC_W) * cam.z;
  const tx = Math.min(0, Math.max(WIN_W - SRC_W * k, WIN_W / 2 - cam.x * k));
  const ty = Math.min(0, Math.max(WIN_H - SRC_H * k, WIN_H / 2 - cam.y * k));
  return (
    <div
      style={{
        width: WIN_W,
        height: WIN_H + BAR,
        borderRadius: 18,
        overflow: "hidden",
        background: "#1b1f2c",
        boxShadow: `0 40px 100px rgba(0,0,0,0.6), 0 0 0 1.5px ${C.line}`,
      }}
    >
      <div style={{ height: BAR, display: "flex", alignItems: "center", gap: 10, padding: "0 18px" }}>
        {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
          <div key={c} style={{ width: 13, height: 13, borderRadius: "50%", background: c }} />
        ))}
        <div
          style={{
            marginLeft: 22,
            flex: 1,
            height: 28,
            borderRadius: 8,
            background: "#0f121b",
            display: "flex",
            alignItems: "center",
            padding: "0 14px",
            fontFamily: mono,
            fontSize: 16,
            color: C.muted,
          }}
        >
          localhost:8000 · Chokepoint · FalkorDB Cloud (ap-south-1) · Gemini 3.5 Flash
        </div>
      </div>
      <div style={{ position: "relative", width: WIN_W, height: WIN_H, overflow: "hidden", background: "#fafafa" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: SRC_W, height: SRC_H, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${k})` }}>
          <OffthreadVideo src={staticFile(src)} muted style={{ width: SRC_W, height: SRC_H }} />
          {callouts.map((c, i) => {
            const p = spring({ frame: frame - s(c.from), fps: 30, config: { damping: 13 } });
            const out = interpolate(t, [c.to - 0.25, c.to], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            if (t < c.from || t > c.to) return null;
            const col = c.color ?? C.accent;
            return (
              <div key={i} style={{ position: "absolute", left: c.x - 8, top: c.y - 8, width: c.w + 16, height: c.h + 16, opacity: out }}>
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    borderRadius: 12,
                    border: `${4 / cam.z}px solid ${col}`,
                    boxShadow: `0 0 0 ${interpolate(p, [0, 1], [30, 0])}px ${col}33`,
                    transform: `scale(${interpolate(p, [0, 1], [1.15, 1])})`,
                    opacity: p,
                  }}
                />
                {c.label ? (
                  <div
                    style={{
                      position: "absolute",
                      left: 0,
                      [c.below ? "top" : "bottom"]: `calc(100% + ${10 / cam.z}px)`,
                      transformOrigin: c.below ? "0 0" : "0 100%",
                      transform: `scale(${(1 / cam.z) * interpolate(p, [0, 1], [0.7, 1])})`,
                      opacity: p,
                      whiteSpace: "nowrap",
                      fontFamily: display,
                      fontWeight: 800,
                      fontSize: 30,
                      color: "#fff",
                      background: col,
                      padding: "8px 16px",
                      borderRadius: 10,
                    }}
                  >
                    {c.label}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const STEPS = ["Find", "Check", "Prove", "Explain", "Remember", "Re-check", "Ask", "Show work"];

export const Steps: React.FC<{ active: number }> = ({ active }) => (
  <div style={{ position: "absolute", left: 60, bottom: 44, display: "flex", gap: 12, alignItems: "center" }}>
    {STEPS.map((name, i) => (
      <React.Fragment key={name}>
        <div
          style={{
            fontFamily: mono,
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: i === active ? "#fff" : i < active ? C.text : C.muted,
            background: i === active ? C.accent : "transparent",
            border: `1.5px solid ${i === active ? C.accent : C.line}`,
            padding: "7px 12px",
            borderRadius: 10,
          }}
        >
          {i + 1} {name}
        </div>
        {i < STEPS.length - 1 ? <div style={{ width: 14, height: 2, background: C.line }} /> : null}
      </React.Fragment>
    ))}
  </div>
);

/** Left: the real recording. Right: what is happening under the hood. */
export const Footage: React.FC<{
  clip: string;
  speed: string;
  step: number;
  cams?: Cam[];
  callouts?: Callout[];
  children: React.ReactNode;
}> = ({ clip, speed, step, cams, callouts, children }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const inP = spring({ frame, fps, config: { damping: 18 } });
  const out = interpolate(frame, [durationInFrames - 7, durationInFrames], [1, 0], { extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: out }}>
      <Bg />
      <div style={{ position: "absolute", left: 60, top: 104, transform: `translateY(${interpolate(inP, [0, 1], [60, 0])}px)`, opacity: Math.min(1, inP * 1.5) }}>
        <Browser src={clip} cams={cams} callouts={callouts} />
        <div style={{ position: "absolute", top: -42, left: 0, display: "flex", gap: 10 }}>
          <Chip size={17} bg="#e5484d" color="#fff" style={{ padding: "5px 12px", borderRadius: 999, border: "none", fontFamily: mono, letterSpacing: "0.08em" }}>
            ● REC · LIVE RUN · 2 OCT 2026
          </Chip>
          <Chip size={17} style={{ padding: "5px 12px", borderRadius: 999, fontFamily: mono, letterSpacing: "0.08em" }}>
            {speed}
          </Chip>
        </div>
      </div>
      <div style={{ position: "absolute", left: 1290, right: 64, top: 104, bottom: 120 }}>{children}</div>
      <Steps active={step} />
    </AbsoluteFill>
  );
};
