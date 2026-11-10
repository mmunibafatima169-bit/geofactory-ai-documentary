/** Reusable documentary chrome: vignette, grade, lower third, kinetic words, labels. */
import React from "react";
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { C, FONT } from "../theme";

export const Grade: React.FC = () => (
  <>
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(ellipse at 50% 45%, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.0) 45%, rgba(0,0,0,0.55) 100%)",
        pointerEvents: "none",
      }}
    />
    <AbsoluteFill
      style={{
        boxShadow: "inset 0 0 260px 90px rgba(0,0,0,0.6)",
        pointerEvents: "none",
      }}
    />
  </>
);

export const KineticWord: React.FC<{
  text: string;
  delay: number;
  highlight?: boolean;
  size?: number;
}> = ({ text, delay, highlight, size = 96 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 14, stiffness: 170 } });
  return (
    <span
      style={{
        display: "inline-block",
        background: highlight ? C.accent : C.text,
        color: C.ink,
        fontFamily: FONT,
        fontWeight: 900,
        fontSize: size,
        lineHeight: 1.06,
        padding: "2px 22px",
        marginRight: 16,
        marginBottom: 12,
        transform: `translateY(${(1 - s) * 110}px) rotate(${(1 - s) * -4}deg)`,
        opacity: s,
      }}
    >
      {text}
    </span>
  );
};

export const LowerThird: React.FC<{
  kicker: string;
  title: string;
  delay?: number;
}> = ({ kicker, title, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 16, stiffness: 120 } });
  return (
    <div
      style={{
        position: "absolute",
        left: 96,
        bottom: 88,
        display: "flex",
        alignItems: "center",
        gap: 18,
        background: "rgba(10,16,24,0.86)",
        borderLeft: `6px solid ${C.accent}`,
        padding: "16px 30px",
        opacity: s,
        transform: `translateX(${(1 - s) * -40}px)`,
        fontFamily: FONT,
      }}
    >
      <span style={{ color: C.accent, fontWeight: 800, fontSize: 24, letterSpacing: "0.2em" }}>
        {kicker}
      </span>
      <span style={{ color: C.muted, fontSize: 24, letterSpacing: "0.08em" }}>{title}</span>
    </div>
  );
};

export const MapLabel: React.FC<{
  x: number;
  y: number;
  text: string;
  delay?: number;
  color?: string;
}> = ({ x, y, text, delay = 0, color = C.text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 15 } });
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        opacity: s,
        transform: `translateY(${(1 - s) * 18}px)`,
        fontFamily: FONT,
      }}
    >
      <div style={{ width: 3, height: 30, background: color, marginLeft: 3 }} />
      <div
        style={{
          background: "rgba(10,16,24,0.9)",
          border: `1px solid ${C.hairline}`,
          padding: "7px 14px",
          fontSize: 26,
          fontWeight: 800,
          color,
          letterSpacing: "0.14em",
          whiteSpace: "nowrap",
        }}
      >
        {text}
      </div>
    </div>
  );
};

/** Section eyebrow used at the top-left of explanatory scenes. */
export const Eyebrow: React.FC<{ text: string; delay?: number }> = ({ text, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 18 } });
  return (
    <div
      style={{
        position: "absolute",
        left: 96,
        top: 84,
        color: C.accent,
        fontFamily: FONT,
        fontSize: 24,
        fontWeight: 800,
        letterSpacing: "0.34em",
        opacity: s,
        transform: `translateY(${(1 - s) * -16}px)`,
      }}
    >
      {text}
    </div>
  );
};
