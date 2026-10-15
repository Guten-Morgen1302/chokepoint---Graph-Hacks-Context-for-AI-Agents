import React from "react";
import { interpolate, spring, useCurrentFrame } from "remotion";
import { Chip, Footage, H, Kicker, M, P, Pop, Slam } from "./ui";
import { C, display, mono, s } from "./theme";

/* Times are seconds inside each sped-up clip; x/y are pixels of the 1440×900 recording (see video/README.md). */

export const TriageScene: React.FC = () => (
  <Footage
    clip="clips/c1_triage.mp4"
    speed="1×"
    step={0}
    cams={[
      { t: 0, x: 720, y: 450, z: 1 },
      { t: 1.1, x: 420, y: 255, z: 1.6 },
      { t: 3.2, x: 430, y: 600, z: 1.3 },
    ]}
    callouts={[
      { from: 1.1, to: 2.2, x: 28, y: 192, w: 700, h: 52, label: "algo.maxFlow · no AI yet", below: true },
      { from: 3.5, to: 5, x: 722, y: 568, w: 56, h: 150, label: "crown jewels", color: C.jewel, below: true },
    ]}
  >
    <Kicker>Finding F-1 · a CI token leaked</Kicker>
    <H size={60} style={{ marginTop: 14 }}>
      Step 1:
      <br />
      <span style={{ color: C.accent }}>pure graph maths.</span>
    </H>
    <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
      <Pop at={0.9} from="left"><Chip><M color={C.accentSoft}>algo.bfs</M> → 2 crown jewels reachable</Chip></Pop>
      <Pop at={1.6} from="left"><Chip><M color={C.accentSoft}>algo.maxFlow</M> → cut 3 grants, cost 5</Chip></Pop>
      <Pop at={2.4} from="left"><Chip>Revoke everything it holds: cost 19</Chip></Pop>
    </div>
    <Pop at={3.3}>
      <P size={26} style={{ marginTop: 30 }}>
        Cost = how much each grant is actually used. Cheap to cut = nobody needs it.
      </P>
    </Pop>
  </Footage>
);

const TOOLS = [
  { at: 0.4, name: "explain_grant", what: "reads runbooks, tickets, chat" },
  { at: 2.0, name: "what_if keep G-102", what: "DR runbook needs it → cost 6" },
  { at: 8.1, name: "choose_plan P1", what: "server re-runs maxFlow" },
];

export const AgentScene: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <Footage
      clip="clips/c2_agent.mp4"
      speed="1.75×"
      step={1}
      cams={[
        { t: 0, x: 1140, y: 520, z: 1.55 },
        { t: 7.7, x: 1140, y: 520, z: 1.55 },
        { t: 8.2, x: 420, y: 250, z: 1.5 },
      ]}
      callouts={[
        { from: 2.0, to: 7.7, x: 874, y: 496, w: 470, h: 30, label: "keep G-102 because doc:dr-runbook" },
        { from: 8.5, to: 10, x: 28, y: 192, w: 690, h: 76, label: "✓ Severed · algo.maxFlow = 0", color: "#1f9d55", below: true },
      ]}
    >
      <Kicker>Step 2 · Gemini reviews the cut</Kicker>
      <H size={56} style={{ marginTop: 14 }}>
        Cheapest isn't
        <br />
        <span style={{ color: C.accent }}>always safe.</span>
      </H>
      <div style={{ marginTop: 34, display: "flex", flexDirection: "column", gap: 14 }}>
        {TOOLS.map((t) => {
          const p = spring({ frame: frame - s(t.at), fps: 30, config: { damping: 13 } });
          return (
            <div key={t.name} style={{ opacity: p, transform: `translateX(${(1 - p) * -40}px)` }}>
              <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 22, color: C.accentSoft }}>{t.name}</div>
              <div style={{ fontFamily: display, fontSize: 23, color: C.muted }}>{t.what}</div>
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 34 }}>
        <Slam at={8.3} size={58} color={C.green}>
          cost 6 · DR safe ✓
        </Slam>
      </div>
      <Pop at={8.8}>
        <P size={24} style={{ marginTop: 16 }}>
          +1 cost buys a disaster recovery that still works.
        </P>
      </Pop>
    </Footage>
  );
};

export const CiteScene: React.FC = () => (
  <Footage
    clip="clips/c3_cite.mp4"
    speed="1×"
    step={1}
    cams={[
      { t: 0, x: 700, y: 270, z: 1.45 },
      { t: 0.5, x: 700, y: 270, z: 1.45 },
      { t: 1.3, x: 1200, y: 150, z: 1.9 },
    ]}
    callouts={[
      { from: 0, to: 0.6, x: 855, y: 272, w: 125, h: 22 },
      { from: 1.1, to: 4.4, x: 978, y: 78, w: 444, h: 100, label: "DR Failover Runbook §3, verbatim", below: true },
    ]}
  >
    <Kicker>Every claim has a source</Kicker>
    <H size={56} style={{ marginTop: 14 }}>
      Click a citation.
      <br />
      <span style={{ color: C.accent }}>Read the proof.</span>
    </H>
    <Pop at={1.4}>
      <P size={27} style={{ marginTop: 34 }}>
        A cite only counts if the agent was actually shown that doc, ticket or message in this run.
      </P>
    </Pop>
    <Pop at={2.6}>
      <Chip style={{ marginTop: 26 }} color={C.jewel} size={24}>
        ✗ invented citation → rejected, plan falls back
      </Chip>
    </Pop>
  </Footage>
);

const CHAIN = ["Ticket SEC-412", "Asha Rao", "Ben Kim", "#platform-ops", "who knows"];

export const BrainScene: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <Footage
      clip="clips/c4_brain.mp4"
      speed="1.2×"
      step={3}
      cams={[
        { t: 0, x: 900, y: 420, z: 1.1 },
        { t: 0.6, x: 1200, y: 330, z: 1.75 },
        { t: 6.6, x: 1200, y: 330, z: 1.75 },
        { t: 7.0, x: 720, y: 450, z: 1 },
      ]}
      callouts={[
        { from: 1.0, to: 3.4, x: 978, y: 168, w: 444, h: 62, label: "requested · approved", below: true },
        { from: 3.4, to: 6.4, x: 978, y: 452, w: 444, h: 86, label: "#platform-ops: \"can go\"", below: true },
      ]}
    >
      <Kicker color={C.accentSoft}>Track 03 · Company brain</Kicker>
      <H size={54} style={{ marginTop: 14 }}>
        Why does this
        <br />
        <span style={{ color: C.accent }}>access exist?</span>
      </H>
      <div style={{ marginTop: 34, display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center" }}>
        {CHAIN.map((c, i) => {
          const p = spring({ frame: frame - s(0.8 + i * 0.55), fps: 30, config: { damping: 13 } });
          return (
            <React.Fragment key={c}>
              <div
                style={{
                  opacity: p,
                  transform: `scale(${interpolate(p, [0, 1], [0.7, 1])})`,
                  fontFamily: display,
                  fontWeight: 700,
                  fontSize: 22,
                  padding: "10px 14px",
                  borderRadius: 12,
                  background: i === 0 ? C.accent : C.panel,
                  color: "#fff",
                  border: `1.5px solid ${i === 0 ? "transparent" : C.line}`,
                }}
              >
                {c}
              </div>
              {i < CHAIN.length - 1 ? <div style={{ opacity: p, fontFamily: mono, color: C.muted }}>→</div> : null}
            </React.Fragment>
          );
        })}
      </div>
      <Pop at={4.0}>
        <P size={25} style={{ marginTop: 30 }}>
          Tickets, people, chat and policy are nodes in the same FalkorDB graph as the access itself. One query, no RAG guesswork.
        </P>
      </Pop>
    </Footage>
  );
};

export const AcceptScene: React.FC = () => (
  <Footage
    clip="clips/c5_accept.mp4"
    speed="1.5×"
    step={4}
    cams={[
      { t: 0, x: 1140, y: 560, z: 1.3 },
      { t: 0.6, x: 1145, y: 610, z: 1.65 },
      { t: 4.9, x: 1145, y: 610, z: 1.65 },
      { t: 5.6, x: 1140, y: 450, z: 1.25 },
    ]}
    callouts={[
      { from: 0.9, to: 2.7, x: 888, y: 484, w: 524, h: 62, label: "why it stays" },
      { from: 2.7, to: 3.5, x: 888, y: 570, w: 524, h: 44, label: "review by" },
      { from: 3.5, to: 4.9, x: 888, y: 654, w: 524, h: 50, label: "sources must exist in the graph", below: true },
    ]}
  >
    <Kicker color={C.accentSoft}>Track 02 · Memory</Kicker>
    <H size={54} style={{ marginTop: 14 }}>
      A person accepts
      <br />
      the risk. <span style={{ color: C.accent }}>The graph remembers.</span>
    </H>
    <div style={{ marginTop: 34, display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
      <Pop at={1.0} from="left"><Chip size={24}>G-102 stays: DR failover runs as deployer</Chip></Pop>
      <Pop at={2.4} from="left"><Chip size={24}>reason · review date · cited sources</Chip></Pop>
      <Pop at={3.8} from="left"><Chip size={24} color="#fff" bg={C.accent} style={{ border: "none" }}>The agent can only propose. A human confirms.</Chip></Pop>
    </div>
  </Footage>
);

export const RecheckScene: React.FC = () => (
  <Footage
    clip="clips/c6_recheck.mp4"
    speed="1×"
    step={5}
    cams={[
      { t: 0, x: 1140, y: 600, z: 1.5 },
      { t: 1.6, x: 1140, y: 560, z: 1.75 },
    ]}
    callouts={[
      { from: 0.2, to: 1.4, x: 868, y: 645, w: 542, h: 38, label: "a change lands in the graph", below: true },
      { from: 1.7, to: 7.3, x: 866, y: 496, w: 546, h: 82, label: "▲ re-checked itself", color: "#c2410c" },
    ]}
  >
    <Kicker color={C.warn}>Memory that re-checks itself</Kicker>
    <H size={54} style={{ marginTop: 14 }}>
      The world changed.
      <br />
      <span style={{ color: C.warn }}>The decision noticed.</span>
    </H>
    <div style={{ marginTop: 34, display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
      <Pop at={0.8} from="left"><Chip size={24}>Platform grants deployer READS hr-payroll-db</Chip></Pop>
      <Pop at={1.8} from="left">
        <Chip size={24} color={C.bg} bg={C.warn} style={{ border: "none" }}>▲ NEEDS REVIEW · now also reaches hr-payroll-db</Chip>
      </Pop>
    </div>
    <Pop at={3.2}>
      <P size={24} style={{ marginTop: 30 }}>
        Each decision stores what it was protecting. New paths, removed grants, deleted sources or a passed review date flip its badge.
      </P>
    </Pop>
    <Pop at={4.6}>
      <div style={{ marginTop: 20, fontFamily: mono, fontSize: 19, color: C.muted }}>SUPERSEDED › WITHDRAWN › STALE › NEEDS_REVIEW › HOLDS</div>
    </Pop>
  </Footage>
);

export const AskScene: React.FC = () => (
  <Footage
    clip="clips/c7_ask.mp4"
    speed="2×"
    step={6}
    cams={[
      { t: 0, x: 790, y: 150, z: 1.45 },
      { t: 1.3, x: 720, y: 450, z: 1 },
      { t: 2.6, x: 430, y: 330, z: 1.3 },
      { t: 8.2, x: 430, y: 330, z: 1.3 },
      { t: 8.5, x: 1140, y: 690, z: 1.6 },
    ]}
    callouts={[
      { from: 0, to: 1.2, x: 236, y: 116, w: 1112, h: 44, label: "plain-English question", below: true },
      { from: 2.8, to: 8.1, x: 28, y: 192, w: 640, h: 50, label: "G-102 remembered → plan routes around it", below: true },
      { from: 8.7, to: 11.2, x: 870, y: 518, w: 545, h: 345, label: "cites SEC-412 · msg:po-01" },
    ]}
  >
    <Kicker>Ask anything</Kicker>
    <H size={50} style={{ marginTop: 14 }}>
      "Why does ci-deploy
      <br />
      have <span style={{ color: C.accent }}>deployer?</span>"
    </H>
    <div style={{ marginTop: 34, display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
      <Pop at={2.8} from="left"><Chip size={23}>Memory feeds the next run: cheapest cut is now cost 6, +0</Chip></Pop>
      <Pop at={4.6} from="left"><Chip size={23}>3 jewels now: hr-payroll-db joined the graph</Chip></Pop>
      <Pop at={8.6} from="left">
        <Chip size={23} color="#fff" bg={C.accent} style={{ border: "none" }}>Answer: a 2023 migration grant, now obsolete</Chip>
      </Pop>
    </div>
  </Footage>
);

export const EvidenceScene: React.FC = () => (
  <Footage
    clip="clips/c8_evidence.mp4"
    speed="1×"
    step={7}
    cams={[
      { t: 0, x: 720, y: 450, z: 1 },
      { t: 0.9, x: 420, y: 500, z: 1.3 },
      { t: 4.8, x: 420, y: 400, z: 1.35 },
    ]}
    callouts={[
      { from: 0.8, to: 1.85, x: 26, y: 448, w: 340, h: 30, label: "the whole run, auditable", below: true },
      { from: 5.0, to: 7.6, x: 30, y: 296, w: 680, h: 180, label: "CALL algo.maxFlow(...)" },
    ]}
  >
    <Kicker>No black box</Kicker>
    <H size={56} style={{ marginTop: 14 }}>
      Every query
      <br />
      <span style={{ color: C.accent }}>on screen.</span>
    </H>
    <div style={{ marginTop: 34, display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
      <Pop at={1.0} from="left"><Chip size={24}>29 queries · 3 algo.maxFlow · 877 ms</Chip></Pop>
      <Pop at={2.0} from="left"><Chip size={24}>Cypher + params for every step</Chip></Pop>
      <Pop at={3.0} from="left"><Chip size={24}>FalkorDB Cloud, Mumbai region</Chip></Pop>
    </div>
  </Footage>
);
