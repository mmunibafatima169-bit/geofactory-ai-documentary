/*
 * VeniceColdOpen — cinematic globe-to-Venice zoom title sequence.
 * GeoFactory Studio · Remotion template v1 (design tokens mirror
 * geofactory/studio/design_tokens.py — keep both in sync).
 *
 * Data: Natural Earth 1:110m Admin 0 Countries (public domain),
 * served as a static file and loaded with delayRender.
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const INK = "#0A1018";
const OCEAN = "#163E5A";
const LAND = "#22384E";
const LAND_STROKE = "#3A4E66";
const ITALY = "#B89264";
const ACCENT = "#F2C14E";
const ALERT = "#E23A2E";
const TEXT = "#F5F1E8";
const MUTED = "#8B94A3";

const VENICE: [number, number] = [12.3371, 45.4371];
const MAP_W = 1280;
const MAP_H = 640; // 2:1 equirectangular
const Y_OFF = 40;

interface Feature {
  properties: { NAME_EN?: string; NAME?: string; [k: string]: unknown };
  geometry: { type: string; coordinates: unknown };
}

const project = (lon: number, lat: number): [number, number] => [
  ((lon + 180) / 360) * MAP_W,
  ((90 - lat) / 180) * MAP_H + 0 * Y_OFF,
];

function featureToPath(f: Feature): string {
  const coords = f.geometry.coordinates as number[][][] | number[][][][];
  const rings: number[][][] =
    f.geometry.type === "Polygon"
      ? (coords as number[][][])
      : (coords as number[][][][]).flat();
  let d = "";
  for (const ring of rings) {
    for (let i = 0; i < ring.length; i++) {
      const [x, y] = project(ring[i][0], ring[i][1]);
      d += `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    }
    d += "Z";
  }
  return d;
}

const Word: React.FC<{ text: string; yellow?: boolean; delay: number }> = ({
  text,
  yellow,
  delay,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 14, stiffness: 160 } });
  return (
    <span
      style={{
        display: "inline-block",
        background: yellow ? ACCENT : TEXT,
        color: INK,
        fontWeight: 900,
        fontFamily: "DejaVu Sans, sans-serif",
        padding: "4px 18px",
        marginRight: 14,
        fontSize: 78,
        letterSpacing: "0.02em",
        transform: `translateY(${(1 - s) * 90}px) rotate(${(1 - s) * -4}deg)`,
        opacity: s,
      }}
    >
      {text}
    </span>
  );
};

export const VeniceColdOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const [handle] = useState(() => delayRender("Loading Natural Earth data"));
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

  const paths = useMemo(() => {
    if (!world) return { land: "", italy: "" };
    let land = "";
    let italy = "";
    for (const f of world) {
      const name = f.properties.NAME_EN ?? f.properties.NAME ?? "";
      if (name === "Italy") italy += featureToPath(f);
      else land += featureToPath(f);
    }
    return { land, italy };
  }, [world]);

  // Globe-style zoom: world view → Venice basin. transformOrigin is pinned
  // to Venice's absolute pixel position so the scale zooms exactly onto it.
  const zoom = spring({
    frame: frame - 22,
    fps,
    config: { damping: 22, stiffness: 60, mass: 1.2 },
    durationInFrames: 66,
  });
  const scale = 1 + zoom * 11;
  const [vx, vy] = project(VENICE[0], VENICE[1]);
  const originX = (vx / MAP_W) * 100;
  const originY = ((vy + Y_OFF) / 720) * 100;

  const pulse = (frame - 80) % 40;
  const pulseOn = frame > 80 && frame < 178;
  const ringR = 10 + (pulse / 40) * 46;
  const ringO = pulseOn ? Math.max(0, 1 - pulse / 40) : 0;

  const labelSpring = spring({ frame: frame - 100, fps, config: { damping: 15 } });
  const lowerSpring = spring({ frame: frame - 148, fps, config: { damping: 16 } });

  return (
    <AbsoluteFill style={{ background: INK, fontFamily: "DejaVu Sans, sans-serif" }}>
      <AbsoluteFill
        style={{
          transform: `scale(${scale})`,
          transformOrigin: `${originX}% ${originY}%`,
        }}
      >
        <svg
          viewBox={`0 0 ${MAP_W} ${MAP_H}`}
          width={MAP_W}
          height={MAP_H}
          style={{ position: "absolute", top: Y_OFF, left: 0 }}
        >
          <rect x={0} y={0} width={MAP_W} height={MAP_H} fill={OCEAN} opacity={0.35} />
          <path d={paths.land} fill={LAND} stroke={LAND_STROKE} strokeWidth={0.6 / scale} />
          <path d={paths.italy} fill={ITALY} stroke={TEXT} strokeWidth={0.9 / scale} />
          {pulseOn && (
            <>
              <circle cx={vx} cy={vy} r={ringR / scale * 12} fill="none" stroke={ACCENT} strokeWidth={2.4 / scale * 12} opacity={ringO} />
              <circle cx={vx} cy={vy} r={6 / scale * 12} fill={ALERT} stroke={TEXT} strokeWidth={1.6 / scale * 12} />
            </>
          )}
        </svg>
      </AbsoluteFill>

      {/* Venice location label */}
      {frame > 88 && (
        <div
          style={{
            position: "absolute",
            left: "52%",
            top: "56%",
            transform: `translateY(${(1 - labelSpring) * 24}px)`,
            opacity: labelSpring,
          }}
        >
          <div style={{ width: 3, height: 34, background: ACCENT, marginLeft: 2 }} />
          <div
            style={{
              background: "rgba(10,16,24,0.88)",
              border: "1px solid #2E3E54",
              padding: "8px 14px",
              fontSize: 26,
              fontWeight: 800,
              color: TEXT,
              letterSpacing: "0.14em",
            }}
          >
            VENICE, ITALY
          </div>
        </div>
      )}

      {/* Kinetic headline */}
      {frame > 116 && (
        <div style={{ position: "absolute", left: 72, top: 84 }}>
          <div style={{ color: ACCENT, fontSize: 20, fontWeight: 800, letterSpacing: "0.32em", marginBottom: 14 }}>
            WHY IT IS HAPPENING
          </div>
          <div>
            <Word text="VENICE" delay={122} />
            <Word text="IS" delay={130} />
            <Word text="SINKING" yellow delay={138} />
          </div>
        </div>
      )}

      {/* Lower third */}
      {frame > 146 && (
        <div
          style={{
            position: "absolute",
            left: 72,
            bottom: 64,
            opacity: lowerSpring,
            transform: `translateX(${(1 - lowerSpring) * -30}px)`,
            display: "flex",
            alignItems: "center",
            gap: 14,
            background: "rgba(10,16,24,0.82)",
            borderLeft: `5px solid ${ACCENT}`,
            padding: "12px 22px",
          }}
        >
          <span style={{ color: ACCENT, fontWeight: 800, fontSize: 20, letterSpacing: "0.2em" }}>CHAPTER 01</span>
          <span style={{ color: MUTED, fontSize: 20, letterSpacing: "0.08em" }}>THE CITY ON WATER</span>
        </div>
      )}

      {/* cinematic vignette */}
      <AbsoluteFill
        style={{
          boxShadow: "inset 0 0 180px 60px rgba(0,0,0,0.55)",
          background: "transparent",
        }}
      />
    </AbsoluteFill>
  );
};
