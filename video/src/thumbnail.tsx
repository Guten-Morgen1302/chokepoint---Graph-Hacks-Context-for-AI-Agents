import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { C, display, mono } from "./theme";

/** YouTube thumbnail 1280×720: both screens are real frames from the 2 Oct live run. */
const Shot: React.FC<{ src: string; rotate: number; left: number; top: number; w: number; h: number }> = ({ src, rotate, left, top, w, h }) => (
  <div
    style={{
      position: "absolute",
      left,
      top,
      width: w + 12,
      height: h + 12,
      padding: 6,
      borderRadius: 16,
      background: "#1b1f2c",
      transform: `rotate(${rotate}deg)`,
      boxShadow: "0 30px 70px rgba(0,0,0,0.6), 0 0 0 2px #2a3042",
    }}
  >
    <div style={{ width: w, height: h, borderRadius: 11, overflow: "hidden" }}>
      <Img src={staticFile(src)} style={{ width: w, height: h, objectFit: "cover", objectPosition: "left top" }} />
    </div>
  </div>
);

export const Thumbnail: React.FC = () => (
  <AbsoluteFill style={{ background: `radial-gradient(circle at 75% 40%, #18245a 0%, ${C.bg} 58%)`, overflow: "hidden" }}>
    <div style={{ position: "absolute", left: 56, top: 52, width: 560 }}>
      <div
        style={{
          display: "inline-block",
          fontFamily: mono,
          fontWeight: 700,
          fontSize: 22,
          letterSpacing: "0.12em",
          color: "#fff",
          background: C.accent,
          padding: "8px 16px",
          borderRadius: 10,
        }}
      >
        FALKORDB · GRAPH HACKS
      </div>
      <div style={{ fontFamily: display, fontWeight: 800, fontSize: 104, lineHeight: 0.9, letterSpacing: "-0.045em", color: C.text, marginTop: 26 }}>
        Token leaked.
      </div>
      <div style={{ fontFamily: display, fontWeight: 800, fontSize: 104, lineHeight: 0.9, letterSpacing: "-0.045em", color: C.accent, marginTop: 6 }}>
        Safe fix,
        <br />
        proven.
      </div>
      <div style={{ fontFamily: display, fontWeight: 700, fontSize: 34, color: C.text, marginTop: 34 }}>
        AI agent + <span style={{ color: C.green }}>algo.maxFlow = 0 ✓</span>
      </div>
    </div>
    <Shot src="thumb/plan.png" rotate={-4} left={600} top={70} w={620} h={404} />
    <Shot src="thumb/review.png" rotate={3} left={690} top={500} w={520} h={134} />
    <div
      style={{
        position: "absolute",
        right: 36,
        bottom: 26,
        fontFamily: display,
        fontWeight: 800,
        fontSize: 32,
        color: C.text,
        background: "rgba(10,12,18,0.85)",
        padding: "8px 18px",
        borderRadius: 14,
        border: `2px solid ${C.accent}`,
      }}
    >
      <span style={{ color: C.accent }}>✂</span> Chokepoint
    </div>
  </AbsoluteFill>
);
