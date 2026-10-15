import React from "react";
import { AbsoluteFill, Composition, Series } from "remotion";
import { AcceptScene, AgentScene, AskScene, BrainScene, CiteScene, EvidenceScene, RecheckScene, TriageScene } from "./footage";
import { ColdOpen, Logo, Problem, Tracks } from "./intro";
import { End, MinCut, Stats } from "./outro";
import { C, FPS, s } from "./theme";
import { Thumbnail } from "./thumbnail";
import { Banner } from "./banner";

// Footage scenes last exactly as long as their clip (video/public/clips, cut by video/cut_clips.sh).
export const SCENES: { C: React.FC; d: number }[] = [
  { C: ColdOpen, d: s(6) },
  { C: Logo, d: s(4.5) },
  { C: Problem, d: s(9) },
  { C: Tracks, d: s(6.5) },
  { C: TriageScene, d: s(5.0) },
  { C: AgentScene, d: s(10.0) },
  { C: CiteScene, d: s(5.2) },
  { C: MinCut, d: s(12.5) },
  { C: BrainScene, d: s(8.0) },
  { C: AcceptScene, d: s(6.0) },
  { C: RecheckScene, d: s(7.5) },
  { C: AskScene, d: s(11.2) },
  { C: EvidenceScene, d: s(7.8) },
  { C: Stats, d: s(10) },
  { C: End, d: s(8) },
];

export const TOTAL = SCENES.reduce((a, b) => a + b.d, 0);

const Main: React.FC = () => (
  <AbsoluteFill style={{ background: C.bg }}>
    <Series>
      {SCENES.map(({ C: Scene, d }, i) => (
        <Series.Sequence key={i} durationInFrames={d}>
          <Scene />
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);

export const Root: React.FC = () => (
  <>
    <Composition id="Chokepoint" component={Main} durationInFrames={TOTAL} fps={FPS} width={1920} height={1080} />
    <Composition id="Thumbnail" component={Thumbnail} durationInFrames={1} fps={FPS} width={1280} height={720} />
    <Composition id="Banner" component={Banner} durationInFrames={1} fps={FPS} width={1600} height={560} />
  </>
);
