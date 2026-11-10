/**
 * 60-second Venice documentary sample — six scenes, each with its own visual
 * language (no repeated footage, no static slides).
 *
 * S1 cold open      · globe → Venice zoom + kinetic title
 * S2 lagoon map     · animated map, inlets, tide arrows, labels
 * S3 foundations    · technical cross-section, piles driving into strata
 * S4 statistics     · animated chart with counting numbers
 * S5 MOSE           · engineering animation, gates rising against the tide
 * S6 closing        · comparison cities + closing statement
 *
 * Map data: Natural Earth 1:110m Admin 0 Countries (public domain).
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  interpolate,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import facts from "../../../sample60_facts.json";
import { C, FONT, Feature, MAP_H, MAP_W, VENICE, featureToPath, project } from "../theme";
import { Eyebrow, Grade, KineticWord, LowerThird, MapLabel } from "../components/Chrome";

const fact = (id: string): number => {
  const item = facts.claims.find((claim) => claim.id === id);
  if (!item) throw new Error(`Missing fact ledger item: ${id}`);
  return item.value;
};

/* ------------------------------------------------------------------ */
/* shared world-map loader                                             */
/* ------------------------------------------------------------------ */
function useWorld() {
  const [handle] = useState(() => delayRender("Natural Earth"));
  const [world, setWorld] = useState<Feature[] | null>(null);
  useEffect(() => {
    fetch(staticFile("ne110.geojson"))
      .then((r) => r.json())
      .then((d) => {
        setWorld(d.features as Feature[]);
        continueRender(handle);
      })
      .catch(() => continueRender(handle));
  }, [handle]);
  return world;
}

function useMapPaths(world: Feature[] | null, highlight: string[]) {
  return useMemo(() => {
    if (!world) return { land: "", hi: "" };
    let land = "";
    let hi = "";
    for (const f of world) {
      const name = (f.properties.NAME_EN ?? f.properties.NAME ?? "") as string;
      if (highlight.includes(name)) hi += featureToPath(f);
      else land += featureToPath(f);
    }
    return { land, hi };
  }, [world, highlight.join("|")]);
}

/* ------------------------------------------------------------------ */
/* S1 — cold open: globe to Venice                                     */
/* ------------------------------------------------------------------ */
export const S1ColdOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const world = useWorld();
  const { land, hi } = useMapPaths(world, ["Italy"]);

  const zoom = spring({
    frame: frame - 18,
    fps,
    config: { damping: 24, stiffness: 55, mass: 1.3 },
    durationInFrames: 78,
  });
  const scale = 1 + zoom * 13;
  const [vx, vy] = project(VENICE[0], VENICE[1]);
  const originX = (vx / MAP_W) * 100;
  const originY = (vy / MAP_H) * 100;

  const pulse = (frame - 86) % 34;
  const pulseOn = frame > 86;
  const ringR = 0.6 + (pulse / 34) * 2.6;
  const ringO = pulseOn ? Math.max(0, 1 - pulse / 34) : 0;

  const footageOpacity = interpolate(frame, [0, 70, 102], [1, 1, 0], { extrapolateRight: "clamp" });
  const mapOpacity = interpolate(frame, [72, 112], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const footageScale = interpolate(frame, [0, 105], [1.04, 1.14]);

  return (
    <AbsoluteFill style={{ background: C.ink }}>
      {/* Licensed real footage establishes the place before the explanatory map. */}
      {frame < 108 && (
        <AbsoluteFill style={{ opacity: footageOpacity, overflow: "hidden" }}>
          <OffthreadVideo
            src={staticFile("footage/gondolas.webm")}
            startFrom={34}
            muted
            style={{ width: "100%", height: "100%", objectFit: "cover",
                     transform: `scale(${footageScale}) translateY(-1.5%)`, filter: "saturate(0.82) contrast(1.1)" }}
          />
          <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(10,16,24,.82), rgba(10,16,24,.08) 70%)" }} />
          <div style={{ position: "absolute", left: 96, top: 120, fontFamily: FONT }}>
            <div style={{ color: C.accent, fontSize: 24, fontWeight: 800, letterSpacing: "0.32em" }}>A CITY BUILT ON WATER</div>
            <div style={{ color: C.text, fontSize: 86, fontWeight: 900, lineHeight: 0.98, marginTop: 20 }}>VENICE<br />IS SINKING.</div>
          </div>
        </AbsoluteFill>
      )}
      <AbsoluteFill
        style={{
          opacity: mapOpacity,
          transform: `scale(${scale}) translate(${Math.sin(frame / 24) * 2.2}px, ${Math.cos(frame / 31) * 1.4}px)`,
          transformOrigin: `${originX}% ${originY}%`,
        }}
      >
        <svg viewBox={`0 0 ${MAP_W} ${MAP_H}`} width={MAP_W} height={MAP_H}
             style={{ position: "absolute", top: 60, left: 0 }}>
          <defs>
            <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={C.ocean} stopOpacity={0.5} />
              <stop offset="100%" stopColor={C.oceanDeep} stopOpacity={0.75} />
            </linearGradient>
          </defs>
          <rect width={MAP_W} height={MAP_H} fill="url(#sea)" />
          <path d={land} fill={C.land} stroke={C.landStroke} strokeWidth={0.8 / scale} />
          <path d={hi} fill={C.terrain} stroke={C.text} strokeWidth={1.1 / scale} />
          {pulseOn && (
            <>
              <circle cx={vx} cy={vy} r={ringR} fill="none" stroke={C.accent}
                      strokeWidth={0.5} opacity={ringO} />
              <circle cx={vx} cy={vy} r={0.55} fill={C.alert} stroke={C.text} strokeWidth={0.22} />
            </>
          )}
        </svg>
      </AbsoluteFill>

      {frame > 96 && <MapLabel x={1010} y={560} text="VENICE, ITALY" delay={100} />}

      {frame > 120 && (
        <div style={{ position: "absolute", left: 96, top: 120 }}>
          <div style={{ color: C.accent, fontFamily: FONT, fontSize: 26, fontWeight: 800,
                        letterSpacing: "0.34em", marginBottom: 20 }}>
            A CITY AGAINST THE SEA
          </div>
          <KineticWord text="VENICE" delay={126} />
          <KineticWord text="IS" delay={134} />
          <KineticWord text="SINKING" delay={142} highlight />
        </div>
      )}
      <Grade />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* S2 — lagoon map with inlets and tide arrows                         */
/* ------------------------------------------------------------------ */
export const S2LagoonMap: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Stylised lagoon geometry (illustrative schematic, not a survey map)
  const drift = interpolate(frame, [0, 300], [0, -40]);
  const zoom = interpolate(frame, [0, 300], [1.0, 1.12]);
  const arrowPhase = (frame % 60) / 60;

  const inlets = [
    { y: 300, name: "LIDO" },
    { y: 520, name: "MALAMOCCO" },
    { y: 740, name: "CHIOGGIA" },
  ];

  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ transform: `scale(${zoom}) translateX(${drift}px)` }}>
        <svg viewBox="0 0 1920 1080" width={1920} height={1080}>
          <rect width={1920} height={1080} fill={C.oceanDeep} />
          {/* open Adriatic on the right */}
          <rect x={1180} width={740} height={1080} fill={C.ocean} opacity={0.75} />
          {/* mainland on the left */}
          <path d="M0,0 L560,0 C600,220 540,420 600,620 C650,820 560,960 520,1080 L0,1080 Z"
                fill={C.land} stroke={C.landStroke} strokeWidth={2} />
          {/* lagoon water */}
          <path d="M560,0 C620,240 560,430 620,630 C670,830 580,980 540,1080 L1180,1080 L1180,0 Z"
                fill={C.ocean} opacity={0.42} />
          {/* barrier islands with the three inlets */}
          <path d="M1150,0 L1210,0 L1210,250 L1150,250 Z" fill={C.terrain} />
          <path d="M1150,350 L1210,350 L1210,470 L1150,470 Z" fill={C.terrain} />
          <path d="M1150,570 L1210,570 L1210,690 L1150,690 Z" fill={C.terrain} />
          <path d="M1150,790 L1210,790 L1210,1080 L1150,1080 Z" fill={C.terrain} />
          {/* Venice island cluster */}
          <g>
            <ellipse cx={880} cy={430} rx={92} ry={56} fill={C.terrainDark} stroke={C.text} strokeWidth={2.5} />
            <ellipse cx={812} cy={492} rx={40} ry={26} fill={C.terrainDark} opacity={0.85} />
            <ellipse cx={960} cy={372} rx={34} ry={22} fill={C.terrainDark} opacity={0.85} />
          </g>
          {/* animated tide arrows pushing through the inlets */}
          {inlets.map((inlet, i) => {
            const x = 1420 - arrowPhase * 240 - i * 10;
            return (
              <g key={inlet.name} opacity={0.9}>
                <path
                  d={`M${x},${inlet.y} L${x - 110},${inlet.y - 26} L${x - 110},${inlet.y - 9}
                      L${x - 210},${inlet.y - 9} L${x - 210},${inlet.y + 9}
                      L${x - 110},${inlet.y + 9} L${x - 110},${inlet.y + 26} Z`}
                  fill={C.alert}
                  opacity={interpolate(arrowPhase, [0, 0.15, 0.85, 1], [0, 1, 1, 0])}
                />
              </g>
            );
          })}
        </svg>
      </AbsoluteFill>

      <Eyebrow text="THE GEOGRAPHY" delay={4} />
      <MapLabel x={760} y={300} text="VENICE" delay={26} color={C.accent} />
      <MapLabel x={1255} y={250} text="LIDO INLET" delay={54} />
      <MapLabel x={1255} y={470} text="MALAMOCCO INLET" delay={72} />
      <MapLabel x={1255} y={690} text="CHIOGGIA INLET" delay={90} />
      <MapLabel x={150} y={820} text="ITALIAN MAINLAND" delay={120} color={C.muted} />
      <div style={{ position: "absolute", right: 110, top: 140, textAlign: "right", fontFamily: FONT }}>
        <div style={{ color: C.muted, fontSize: 24, letterSpacing: "0.22em" }}>ADRIATIC SEA</div>
      </div>
      <LowerThird kicker={`${fact("fact-islands")} ISLANDS`} title="THREE INLETS TO THE OPEN SEA" delay={150} />
      <Grade />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* S3 — technical cross-section: wooden piles through the strata       */
/* ------------------------------------------------------------------ */
export const S3Foundations: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const strata = [
    { y: 470, h: 120, fill: "#2A4258", label: "LAGOON WATER" },
    { y: 590, h: 130, fill: "#4A3A28", label: "SOFT MUD" },
    { y: 720, h: 130, fill: "#5C4731", label: "CLAY" },
    { y: 850, h: 170, fill: "#6E5637", label: "CAPAROZZOLO — FIRM LAYER" },
  ];

  const piles = Array.from({ length: 14 }, (_, i) => i);
  const camY = interpolate(frame, [0, 360], [0, -70]);

  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ transform: `translateY(${camY}px)` }}>
        <svg viewBox="0 0 1920 1080" width={1920} height={1080}>
          <rect width={1920} height={1080} fill={C.ink} />
          {/* sky / air above the water */}
          <rect y={300} width={1920} height={170} fill="#16222F" />
          {strata.map((s) => (
            <rect key={s.label} y={s.y} width={1920} height={s.h} fill={s.fill} />
          ))}
          {/* strata hairlines */}
          {strata.map((s) => (
            <line key={`l-${s.label}`} x1={0} y1={s.y} x2={1920} y2={s.y}
                  stroke={C.hairline} strokeWidth={2} opacity={0.7} />
          ))}

          {/* wooden piles driving down, staggered */}
          {piles.map((i) => {
            const start = 24 + i * 7;
            const p = spring({ frame: frame - start, fps, config: { damping: 18, stiffness: 90 } });
            const top = 560;
            const full = 300;
            const len = full * p;
            const x = 560 + i * 58;
            return (
              <g key={i}>
                <rect x={x} y={top} width={18} height={len} fill="#8A5F32" stroke="#5C3F22" strokeWidth={2} />
                <polygon points={`${x},${top + len} ${x + 18},${top + len} ${x + 9},${top + len + 22}`} fill="#5C3F22" />
              </g>
            );
          })}

          {/* stone platform + building mass appear after the piles */}
          {frame > 150 && (
            <g opacity={interpolate(frame, [150, 185], [0, 1], { extrapolateRight: "clamp" })}>
              <rect x={520} y={505} width={880} height={56} fill="#9AA3AC" stroke={C.text} strokeWidth={2.5} />
              <rect x={600} y={372} width={300} height={134} fill="#B6BDC4" stroke={C.text} strokeWidth={2} />
              <rect x={940} y={330} width={220} height={176} fill="#A7AFB7" stroke={C.text} strokeWidth={2} />
              <rect x={1200} y={400} width={170} height={106} fill="#B6BDC4" stroke={C.text} strokeWidth={2} />
              <polygon points="1030,250 1160,330 900,330" fill={C.terrain} stroke={C.text} strokeWidth={2} />
            </g>
          )}
        </svg>
      </AbsoluteFill>

      <Eyebrow text="HOW IT WAS BUILT" delay={4} />
      {/* strata callouts */}
      {strata.map((s, i) => (
        <MapLabel key={s.label} x={110} y={s.y + camY + 24} text={s.label} delay={40 + i * 16}
                  color={i === 3 ? C.accent : C.muted} />
      ))}
      {frame > 196 && (
        <div style={{ position: "absolute", right: 110, top: 190, textAlign: "right", fontFamily: FONT }}>
          <div style={{ color: C.text, fontSize: 86, fontWeight: 900, lineHeight: 1 }}>MILLIONS</div>
          <div style={{ color: C.accent, fontSize: 30, fontWeight: 800, letterSpacing: "0.16em", marginTop: 8 }}>
            OF WOODEN PILES
          </div>
        </div>
      )}
      <LowerThird kicker="NO OXYGEN" title="THE TIMBER HARDENED INSTEAD OF ROTTING" delay={250} />
      <Grade />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* S4 — archival evidence morphing into sourced statistics             */
/* ------------------------------------------------------------------ */
export const S4Stats: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const chartReveal = spring({ frame: frame - 78, fps, config: { damping: 24, stiffness: 70 } });
  const archivalOpacity = interpolate(frame, [58, 100], [1, 0], { extrapolateRight: "clamp" });
  const bars = [
    { label: "ACQUA ALTA", sub: "reference threshold", v: fact("fact-acqua-threshold"), color: C.accent, delay: 96 },
    { label: "1966 FLOOD", sub: "Punta Salute datum", v: fact("fact-1966-peak"), color: C.alert, delay: 132 },
    { label: "MOSE LIMIT", sub: "design protection", v: fact("fact-mose-design"), color: C.growth, delay: 168 },
  ];
  const maxV = fact("fact-mose-design");
  const baseY = 830;
  const topY = 330;

  return (
    <AbsoluteFill style={{ background: C.ink }}>
      {/* Public-domain 1896 Grand Canal footage: historical evidence, not decoration. */}
      {frame < 110 && (
        <AbsoluteFill style={{ opacity: archivalOpacity, overflow: "hidden" }}>
          <OffthreadVideo src={staticFile("footage/venice-1896.webm")} muted
            style={{ width: "100%", height: "100%", objectFit: "cover",
                     transform: `scale(${interpolate(frame, [0, 110], [1.02, 1.12])})`,
                     filter: "grayscale(1) sepia(.25) contrast(1.15)" }} />
          <AbsoluteFill style={{ background: "linear-gradient(90deg, rgba(10,16,24,.82), transparent 75%)" }} />
          <div style={{ position: "absolute", left: 96, top: 120, fontFamily: FONT }}>
            <div style={{ color: C.accent, fontSize: 24, fontWeight: 800, letterSpacing: "0.3em" }}>ARCHIVAL FILM · PUBLIC DOMAIN</div>
            <div style={{ color: C.text, fontSize: 96, fontWeight: 900, marginTop: 20 }}>VENICE · 1896</div>
            <div style={{ color: C.muted, fontSize: 28, marginTop: 12 }}>before industrial pumping accelerated subsidence</div>
          </div>
        </AbsoluteFill>
      )}

      <AbsoluteFill style={{ opacity: chartReveal, clipPath: `inset(0 ${100 - chartReveal * 100}% 0 0)`,
                             background: `linear-gradient(160deg, ${C.panel} 0%, ${C.ink} 60%)` }}>
        <svg viewBox="0 0 1920 1080" width={1920} height={1080} style={{ position: "absolute" }}>
          {[100, 200, 300].map((v) => {
            const y = baseY - (v / maxV) * (baseY - topY);
            return <line key={v} x1={420} y1={y} x2={1740} y2={y} stroke={C.hairline} strokeWidth={2} />;
          })}
          <line x1={420} y1={baseY} x2={1740} y2={baseY} stroke={C.text} strokeWidth={4} />
          {bars.map((b, i) => {
            const p = spring({ frame: frame - b.delay, fps, config: { damping: 22, stiffness: 80 } });
            const h = (b.v / maxV) * (baseY - topY) * p;
            const x = 520 + i * 400;
            return (
              <g key={b.label}>
                <rect x={x} y={baseY - h} width={250} height={h} fill={b.color} />
                {/* Sequential emphasis keeps comparison active after each bar settles. */}
                <rect x={x + 7} y={baseY - h + 7} width={236} height={Math.max(0, h - 14)}
                      fill={C.text} opacity={p * (0.035 + 0.045 * (1 + Math.sin(frame / 9 + i * 2.1)))} />
                <rect x={x} y={baseY - h} width={250} height={6} fill={C.text} opacity={0.65} />
                <text x={x + 125} y={baseY + 52} fill={C.text} fontSize={30} fontWeight={800}
                      fontFamily={FONT} textAnchor="middle">{b.label}</text>
                <text x={x + 125} y={baseY + 88} fill={C.muted} fontSize={21}
                      fontFamily={FONT} textAnchor="middle">{b.sub}</text>
              </g>
            );
          })}
          {/* Moving dashed bracket communicates the 106 cm design headroom. */}
          {frame > 190 && (
            <g opacity={interpolate(frame, [190, 215], [0, 1], { extrapolateRight: "clamp" })}>
              <line x1={1650} y1={baseY - (194 / maxV) * (baseY - topY)}
                    x2={1650} y2={topY} stroke={C.accent} strokeWidth={4}
                    strokeDasharray="12 10" strokeDashoffset={-frame * 2.2} />
              <text x={1625} y={500} fill={C.accent} fontSize={30} fontWeight={800}
                    fontFamily={FONT} textAnchor="end">106 CM</text>
              <text x={1625} y={536} fill={C.muted} fontSize={20}
                    fontFamily={FONT} textAnchor="end">DESIGN HEADROOM</text>
            </g>
          )}
        </svg>

        {/* Values never count through unsourced intermediates; only bar geometry animates. */}
        {bars.map((b, i) => {
          const p = spring({ frame: frame - b.delay, fps, config: { damping: 22, stiffness: 80 } });
          const h = (b.v / maxV) * (baseY - topY) * p;
          return (
            <div key={b.label} style={{ position: "absolute", left: 520 + i * 400, width: 250,
                                       top: Math.max(278, baseY - h - 108), textAlign: "center",
                                       opacity: interpolate(p, [0, .15], [0, 1], { extrapolateRight: "clamp" }) }}>
              <span style={{ color: b.color, fontFamily: FONT, fontSize: 88, fontWeight: 900 }}>{b.v}</span>
              <span style={{ color: b.color, fontFamily: FONT, fontSize: 30, fontWeight: 800 }}> cm</span>
            </div>
          );
        })}
        <Eyebrow text="VERIFIED NUMBERS" delay={88} />
        <div style={{ position: "absolute", left: 96, top: 150, fontFamily: FONT }}>
          <div style={{ color: C.text, fontSize: 60, fontWeight: 900 }}>THREE DIFFERENT MEASURES</div>
          <div style={{ color: C.muted, fontSize: 26, marginTop: 10 }}>threshold · measured peak · engineering design limit</div>
        </div>
        <LowerThird kicker="SOURCES" title="KIT / COMUNE DI VENEZIA · ITALIAN MINISTRY / WATER AUTHORITY" delay={255} />
      </AbsoluteFill>
      <Grade />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* S5 — MOSE engineering animation                                     */
/* ------------------------------------------------------------------ */
export const S5Mose: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // gates rotate up from the seabed between frames 70 and 170
  const lift = spring({ frame: frame - 70, fps, config: { damping: 26, stiffness: 45 }, durationInFrames: 100 });
  const angle = interpolate(lift, [0, 1], [86, 16]);

  const seabedY = 820;
  const gateTopY = seabedY - 30 - 260 * Math.cos((angle * Math.PI) / 180); // ≈540 upright
  // Sea rises only to just BELOW the gate crest, otherwise it would read as
  // water spilling over the barrier.
  const seaBase = 640;
  const tide = interpolate(frame, [170, 300], [0, seaBase - (gateTopY + 34)],
                           { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const seaTop = seaBase - tide;
  const lagoonTop = 648;

  const gates = [0, 1, 2, 3, 4];

  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <svg viewBox="0 0 1920 1080" width={1920} height={1080}>
        <defs>
          <linearGradient id="seaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1E5578" />
            <stop offset="100%" stopColor={C.oceanDeep} />
          </linearGradient>
        </defs>
        <rect width={1920} height={1080} fill="#0D1620" />
        {/* lagoon side (left, protected) stays at its calm level */}
        <rect x={0} y={lagoonTop} width={950} height={1080 - lagoonTop} fill={C.ocean} opacity={0.5} />
        <line x1={0} y1={lagoonTop} x2={950} y2={lagoonTop} stroke={C.growth} strokeWidth={3} opacity={0.8} />
        {/* sea side (right) rises against the barrier, crest stays below the gates */}
        <rect x={950} y={seaTop} width={970} height={1080 - seaTop} fill="url(#seaGrad)" opacity={0.95} />
        <line x1={950} y1={seaTop} x2={1920} y2={seaTop} stroke={C.alert} strokeWidth={3} opacity={0.85} />
        {/* seabed */}
        <rect y={seabedY} width={1920} height={260} fill="#4A3A28" />
        <rect y={seabedY} width={1920} height={8} fill="#6E5637" />
        {/* Continuous current lines: visible before and during gate lift. */}
        {[0, 1, 2].map((i) => (
          <g key={`current-${i}`} opacity={0.22 + i * 0.05}
             transform={`translate(${((frame * (1.2 + i * .25)) % 160) - 80} 0)`}>
            <path d={`M0 ${lagoonTop + 42 + i * 54} Q180 ${lagoonTop + 22 + i * 54} 360 ${lagoonTop + 42 + i * 54} T760 ${lagoonTop + 42 + i * 54}`}
                  fill="none" stroke={C.text} strokeWidth={3} />
            <path d={`M1040 ${seaTop + 46 + i * 58} Q1260 ${seaTop + 20 + i * 58} 1480 ${seaTop + 46 + i * 58} T1920 ${seaTop + 46 + i * 58}`}
                  fill="none" stroke={C.text} strokeWidth={3} />
          </g>
        ))}

        {/* caisson housing */}
        <rect x={860} y={seabedY - 36} width={200} height={40} fill="#3B4654" stroke={C.hairline} strokeWidth={2} />

        {/* gates */}
        {gates.map((i) => {
          const x = 880 + i * 34;
          const localAngle = angle + i * 1.1;
          return (
            <g key={i} transform={`translate(${x} ${seabedY - 30}) rotate(${-localAngle})`}>
              <rect x={-12} y={-260} width={24} height={260} fill="#7F8893" stroke="#AEB6BF" strokeWidth={2.5} />
              <rect x={-12} y={-260} width={24} height={34} fill={C.accent} />
            </g>
          );
        })}

        {/* compressed-air indicator */}
        {frame > 56 && frame < 180 && (
          <g opacity={interpolate(frame, [56, 70, 160, 180], [0, 1, 1, 0])}>
            {[0, 1, 2].map((i) => {
              const bubbleY = seabedY - 60 - ((frame * 4 + i * 55) % 190);
              return <circle key={i} cx={830 - i * 18} cy={bubbleY} r={9 + i * 2} fill={C.text} opacity={0.5} />;
            })}
          </g>
        )}

        {/* level-difference indicator between the two sides */}
        {frame > 190 && (
          <g opacity={interpolate(frame, [190, 215], [0, 1], { extrapolateRight: "clamp" })}>
            <line x1={1420} y1={seaTop} x2={1420} y2={lagoonTop} stroke={C.accent} strokeWidth={3} />
            <line x1={1400} y1={seaTop} x2={1440} y2={seaTop} stroke={C.accent} strokeWidth={3} />
            <line x1={1400} y1={lagoonTop} x2={1440} y2={lagoonTop} stroke={C.accent} strokeWidth={3} />
            <text x={1455} y={(seaTop + lagoonTop) / 2 + 10} fill={C.accent} fontSize={30}
                  fontWeight={800} fontFamily={FONT}>HELD DIFFERENCE</text>
          </g>
        )}
      </svg>

      <Eyebrow text="THE ENGINEERING" delay={4} />
      <div style={{ position: "absolute", left: 96, top: 150, fontFamily: FONT }}>
        <div style={{ color: C.text, fontSize: 64, fontWeight: 900 }}>MOSE</div>
        <div style={{ color: C.accent, fontSize: 28, fontWeight: 800, letterSpacing: "0.18em", marginTop: 8 }}>
          78 HOLLOW STEEL GATES
        </div>
      </div>
      {frame > 60 && <MapLabel x={560} y={736} text="COMPRESSED AIR" delay={64} color={C.text} />}
      {frame > 180 && <MapLabel x={1120} y={seaTop - 118} text="TIDE HELD BACK" delay={184} color={C.alert} />}
      {frame > 200 && <MapLabel x={150} y={lagoonTop - 118} text="CITY STAYS DRY" delay={204} color={C.growth} />}
      <LowerThird kicker="FIRST RAISED" title="OCTOBER 2020" delay={230} />
      <Grade />
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------------ */
/* S6 — closing: the same problem elsewhere                            */
/* ------------------------------------------------------------------ */
export const S6Closing: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const world = useWorld();
  const { land, hi } = useMapPaths(world, ["Indonesia", "Thailand", "United States of America", "China", "Italy"]);

  const zoomOut = spring({ frame, fps, config: { damping: 30, stiffness: 40 }, durationInFrames: 120 });
  const scale = interpolate(zoomOut, [0, 1], [5.5, 1.08]);
  const [vx, vy] = project(VENICE[0], VENICE[1]);

  const cities: { name: string; lon: number; lat: number; delay: number; labelLeft?: boolean }[] = [
    { name: "JAKARTA", lon: 106.8, lat: -6.2, delay: 110 },
    { name: "BANGKOK", lon: 100.5, lat: 13.7, delay: 128, labelLeft: true },
    { name: "NEW ORLEANS", lon: -90.1, lat: 29.95, delay: 146, labelLeft: true },
    { name: "SHANGHAI", lon: 121.5, lat: 31.2, delay: 164 },
  ];

  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{
        transform: `scale(${scale}) translate(${Math.sin(frame / 14) * 4}px, ${Math.cos(frame / 19) * 3}px)`,
        transformOrigin: `${(vx / MAP_W) * 100}% ${(vy / MAP_H) * 100}%`,
      }}>
        <svg viewBox={`0 0 ${MAP_W} ${MAP_H}`} width={MAP_W} height={MAP_H}
             style={{ position: "absolute", top: 60, left: 0 }}>
          <rect width={MAP_W} height={MAP_H} fill={C.oceanDeep} opacity={0.6} />
          <path d={land} fill={C.land} stroke={C.landStroke} strokeWidth={0.8} />
          <path d={hi} fill={C.terrain} stroke={C.text} strokeWidth={0.9} />
          {cities.map((c) => {
            const [cx, cy] = project(c.lon, c.lat);
            const p = spring({ frame: frame - c.delay, fps, config: { damping: 16 } });
            const pulsePhase = Math.max(0, ((frame - c.delay) % 42) / 42);
            // labels live inside the SVG so they track the projection exactly
            const flip = c.labelLeft ? -1 : 1;
            const boxW = c.name.length * 10.5 + 18;
            return (
              <g key={c.name} opacity={p}>
                <line x1={vx} y1={vy} x2={cx} y2={cy} stroke={C.accent} strokeWidth={1.5}
                      strokeDasharray="9 10" strokeDashoffset={-frame * 1.8} opacity={0.34} />
                <circle cx={cx} cy={cy} r={4 + p * 3} fill={C.alert} stroke={C.text} strokeWidth={1.2} />
                <circle cx={cx} cy={cy} r={8 + pulsePhase * 16} fill="none" stroke={C.alert} strokeWidth={1.2}
                        opacity={p * 0.65 * (1 - pulsePhase)} />
                <line x1={cx} y1={cy} x2={cx + flip * 16} y2={cy + 22} stroke={C.text} strokeWidth={1.2} opacity={0.8} />
                <rect x={flip > 0 ? cx + 16 : cx - 16 - boxW} y={cy + 12} width={boxW} height={24}
                      fill="rgba(10,16,24,0.88)" stroke={C.hairline} strokeWidth={0.8} />
                <text x={flip > 0 ? cx + 25 : cx - 25 - boxW + 9} y={cy + 29}
                      fill={C.text} fontSize={15} fontWeight={800} fontFamily={FONT}
                      letterSpacing="1.4">{c.name}</text>
              </g>
            );
          })}
          <circle cx={vx} cy={vy} r={5} fill={C.accent} stroke={C.text} strokeWidth={1.4} />
          <rect x={vx + 14} y={vy - 34} width={76} height={23} fill="rgba(10,16,24,0.9)"
                stroke={C.accent} strokeWidth={0.9} />
          <text x={vx + 22} y={vy - 17} fill={C.accent} fontSize={15} fontWeight={800}
                fontFamily={FONT} letterSpacing="1.4">VENICE</text>
        </svg>
      </AbsoluteFill>

      {frame > 60 && (
        <div style={{ position: "absolute", left: 96, top: 120, maxWidth: 1000 }}>
          <KineticWord text="VENICE" delay={64} size={74} />
          <KineticWord text="IS" delay={70} size={74} />
          <KineticWord text="FIRST." delay={76} size={74} highlight />
          <div style={{ marginTop: 14 }}>
            <KineticWord text="NOT" delay={92} size={74} />
            <KineticWord text="ALONE." delay={98} size={74} />
          </div>
        </div>
      )}
      <LowerThird kicker="GEOFACTORY" title="RESEARCH-LED · HUMAN-APPROVED · DRAFT" delay={200} />
      <Grade />
    </AbsoluteFill>
  );
};
