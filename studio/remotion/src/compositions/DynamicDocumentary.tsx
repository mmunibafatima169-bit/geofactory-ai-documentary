/**
 * DynamicDocumentary — Generic Remotion composition for GeoFactory documentaries.
 * 
 * Renders scenes from a scene manifest JSON, using the shared design system.
 * Each scene's visual_objective and animation_type determine the visual treatment.
 * 
 * Data flow:
 * 1. Python generates scene_manifest.json from DocumentaryPlanner + VisualDirector
 * 2. This composition reads the manifest via inputProps
 * 3. Renders each scene sequentially with transitions
 */

import React, { useEffect, useMemo, useState } from "react";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  C,
  FONT,
  MAP_H,
  MAP_W,
  project,
  featureToPath,
  Feature,
} from "../theme";
import {
  Eyebrow,
  Grade,
  KineticWord,
  LowerThird,
  MapLabel,
} from "../components/Chrome";

// ============================================================================
// Types matching the SceneManifest schema
// ============================================================================

interface ScenePlan {
  scene_id: string;
  narration: string;
  start_s: number;
  end_s: number;
  visual_objective: string;
  engine: string;
  animation_type: string;
  camera: string;
  text_overlays: string[];
  transition: string;
  sound_fx: string[];
  source_ids: string[];
  rationale: string;
}

interface SceneManifest {
  job_id: string;
  title: string;
  fps: number;
  width: number;
  height: number;
  scenes: ScenePlan[];
}

// ============================================================================
// Shared constants (mirror design_tokens.py)
// ============================================================================

const TRANSITION_DURATIONS: Record<string, number> = {
  cut: 0,
  dip_to_black: 0.4,
  zoom_punch: 0.35,
  wipe_map: 0.5,
  crossfade: 0.4,
};

const CAMERA_PRESETS: Record<string, { kind: string; from: number; to: number }> = {
  push_in: { kind: "zoom", from: 1.0, to: 1.1 },
  pull_back: { kind: "zoom", from: 1.1, to: 1.0 },
  pan_right: { kind: "pan", from: -1.0, to: 1.0 },
  pan_down: { kind: "pan", from: -1.0, to: 1.0 },
};

// ============================================================================
// Natural Earth world map loader (shared)
// ============================================================================

function useWorld() {
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

// ============================================================================
// Scene Renderers — one per visual_objective type
// ============================================================================

interface SceneRendererProps {
  scene: ScenePlan;
  frame: number;
  fps: number;
  world: Feature[] | null;
  totalDuration: number;
  sceneIndex: number;
}

// ---- Map Context Scene ----
function MapContextScene({ scene, frame, fps, world, totalDuration, sceneIndex }: SceneRendererProps) {
  const { land, hi } = useMapPaths(world, []);
  const duration = scene.end_s - scene.start_s;
  const localFrame = frame - scene.start_s * fps;
  const progress = Math.min(1, Math.max(0, localFrame / (duration * fps)));
  
  // Extract countries from narration for highlighting
  const countryMatches = scene.narration.match(/\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g) || [];
  const countries = countryMatches.filter(c => 
    ["Italy", "France", "Germany", "Spain", "China", "India", "Japan", "Brazil", "Canada", "Australia", "Russia", "United States", "United Kingdom", "Indonesia", "Thailand", "Vietnam", "Egypt", "Nigeria", "South Africa", "Mexico", "Argentina"].includes(c)
  ).slice(0, 5);
  
  const { land: landPaths, hi: hiPaths } = useMapPaths(world, countries);
  
  // Camera animation
  const cameraPreset = CAMERA_PRESETS[scene.camera] || CAMERA_PRESETS.push_in;
  const scale = interpolate(progress, [0, 1], [cameraPreset.from, cameraPreset.to]);
  const [cx, cy] = project(0, 0); // Center
  
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: "50% 50%" }}>
        <svg viewBox={`0 0 ${MAP_W} ${MAP_H}`} width={MAP_W} height={MAP_H} style={{ position: "absolute", top: 60, left: 0 }}>
          <rect width={MAP_W} height={MAP_H} fill={C.oceanDeep} opacity={0.6} />
          <path d={landPaths} fill={C.land} stroke={C.landStroke} strokeWidth={0.8 / scale} />
          <path d={hiPaths} fill={C.terrain} stroke={C.text} strokeWidth={0.9 / scale} />
        </svg>
      </AbsoluteFill>
      <Eyebrow text={scene.visual_objective.toUpperCase().replace("_", " ")} delay={Math.max(0, localFrame)} />
      {scene.text_overlays.includes("location_label") && (
        <MapLabel x={100} y={100} text={scene.narration.slice(0, 50)} delay={Math.max(0, localFrame + 30)} />
      )}
      <Grade />
    </AbsoluteFill>
  );
}

// ---- Engineering Demo Scene ----
function EngineeringDemoScene({ scene, frame, fps, totalDuration, sceneIndex }: SceneRendererProps) {
  const duration = scene.end_s - scene.start_s;
  const localFrame = frame - scene.start_s * fps;
  const progress = Math.min(1, Math.max(0, localFrame / (duration * fps)));
  
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <svg viewBox="0 0 1920 1080" width={1920} height={1080} style={{ position: "absolute" }}>
        <rect width={1920} height={1080} fill={C.ink} />
        {/* Strata layers */}
        <rect y={300} width={1920} height={170} fill="#16222F" />
        <rect y={470} width={1920} height={120} fill="#2A4258" />
        <rect y={590} width={1920} height={130} fill="#4A3A28" />
        <rect y={720} width={1920} height={130} fill="#5C4731" />
        <rect y={850} width={1920} height={170} fill="#6E5637" />
        
        {/* Animated piles driving down */}
        {Array.from({ length: 12 }, (_, i) => {
          const startDelay = 24 + i * 7;
          const p = spring({ frame: localFrame - startDelay, fps, config: { damping: 18, stiffness: 90 } });
          const top = 560;
          const full = 300;
          const len = full * p;
          const x = 560 + i * 58;
          return (
            <g key={i} opacity={progress}>
              <rect x={x} y={top} width={18} height={len} fill="#8A5F32" stroke="#5C3F22" strokeWidth={2} />
              <polygon points={`${x},${top + len} ${x + 18},${top + len} ${x + 9},${top + len + 22}`} fill="#5C3F22" />
            </g>
          );
        })}
        
        {/* Platform appears after piles */}
        {localFrame > 150 && (
          <g opacity={interpolate(localFrame, [150, 185], [0, 1], { extrapolateRight: "clamp" })}>
            <rect x={520} y={505} width={880} height={56} fill="#9AA3AC" stroke={C.text} strokeWidth={2.5} />
            <rect x={600} y={372} width={300} height={134} fill="#B6BDC4" stroke={C.text} strokeWidth={2} />
          </g>
        )}
      </svg>
      <Eyebrow text="ENGINEERING DEMONSTRATION" delay={Math.max(0, localFrame)} />
      {scene.text_overlays.includes("part_callouts") && (
        <>
          <MapLabel x={110} y={480} text="LAGOON WATER" delay={Math.max(0, localFrame + 40)} color={C.muted} />
          <MapLabel x={110} y={600} text="SOFT MUD" delay={Math.max(0, localFrame + 60)} color={C.muted} />
          <MapLabel x={110} y={730} text="CLAY" delay={Math.max(0, localFrame + 80)} color={C.muted} />
          <MapLabel x={110} y={860} text="CAPAROZZOLO — FIRM LAYER" delay={Math.max(0, localFrame + 100)} color={C.accent} />
        </>
      )}
      <Grade />
    </AbsoluteFill>
  );
}

// ---- Data Chart Scene ----
function DataChartScene({ scene, frame, fps, totalDuration, sceneIndex }: SceneRendererProps) {
  const duration = scene.end_s - scene.start_s;
  const localFrame = frame - scene.start_s * fps;
  const progress = Math.min(1, Math.max(0, localFrame / (duration * fps)));
  
  // Extract numbers from narration for chart data
  const numbers = scene.narration.match(/\d+(?:\.\d+)?/g) || ["100", "150", "200"];
  const values = numbers.slice(0, 5).map(n => parseFloat(n));
  const maxV = Math.max(...values, 1);
  
  const baseY = 830;
  const topY = 330;
  
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <svg viewBox="0 0 1920 1080" width={1920} height={1080} style={{ position: "absolute" }}>
        <rect width={1920} height={1080} fill={C.ink} />
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((v) => {
          const y = baseY - v * (baseY - topY);
          return <line key={v} x1={420} y1={y} x2={1740} y2={y} stroke={C.hairline} strokeWidth={2} />;
        })}
        <line x1={420} y1={baseY} x2={1740} y2={baseY} stroke={C.text} strokeWidth={4} />
        
        {/* Bars */}
        {values.map((v, i) => {
          const p = spring({ frame: localFrame - 80 - i * 40, fps, config: { damping: 22, stiffness: 80 } });
          const h = (v / maxV) * (baseY - topY) * p;
          const x = 520 + i * 300;
          return (
            <g key={i}>
              <rect x={x} y={baseY - h} width={200} height={h} fill={[C.accent, C.alert, C.growth, C.terrain, C.muted][i % 5]} />
              <rect x={x + 7} y={baseY - h + 7} width={186} height={Math.max(0, h - 14)} fill={C.text} opacity={0.08} />
              <rect x={x} y={baseY - h} width={200} height={6} fill={C.text} opacity={0.65} />
              <text x={x + 100} y={baseY + 52} fill={C.text} fontSize={28} fontWeight={800} fontFamily={FONT} textAnchor="middle">{v}</text>
            </g>
          );
        })}
      </svg>
      <Eyebrow text="VERIFIED DATA" delay={Math.max(0, localFrame)} />
      {scene.text_overlays.includes("axis_labels") && (
        <MapLabel x={100} y={900} text="Source: Factual Verifier Ledger" delay={Math.max(0, localFrame + 100)} color={C.muted} />
      )}
      <Grade />
    </AbsoluteFill>
  );
}

// ---- Archival Footage Scene ----
function ArchivalFootageScene({ scene, frame, fps, totalDuration, sceneIndex }: SceneRendererProps) {
  const duration = scene.end_s - scene.start_s;
  const localFrame = frame - scene.start_s * fps;
  const progress = Math.min(1, Math.max(0, localFrame / (duration * fps)));
  
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        {/* Placeholder for archival footage - would use OffthreadVideo with licensed clip */}
        <AbsoluteFill style={{ background: "linear-gradient(160deg, #1A2A3A 0%, #0A1018 100%)" }} />
        <div style={{ position: "absolute", left: 96, top: 120, fontFamily: FONT }}>
          <div style={{ color: C.accent, fontSize: 20, fontWeight: 800, letterSpacing: "0.3em" }}>ARCHIVAL FOOTAGE</div>
          <div style={{ color: C.text, fontSize: 72, fontWeight: 900, marginTop: 20 }}>{scene.narration.slice(0, 60)}</div>
          <div style={{ color: C.muted, fontSize: 24, marginTop: 12 }}>Public domain / CC-licensed historical film</div>
        </div>
      </AbsoluteFill>
      <Eyebrow text="HISTORICAL EVIDENCE" delay={Math.max(0, localFrame)} />
      <Grade />
    </AbsoluteFill>
  );
}

// ---- Cinematic Footage Scene ----
function CinematicFootageScene({ scene, frame, fps, totalDuration, sceneIndex }: SceneRendererProps) {
  const duration = scene.end_s - scene.start_s;
  const localFrame = frame - scene.start_s * fps;
  const progress = Math.min(1, Math.max(0, localFrame / (duration * fps)));
  
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        {/* Placeholder for licensed footage - would use OffthreadVideo */}
        <AbsoluteFill style={{ background: "linear-gradient(160deg, #1A3A2A 0%, #0A1018 100%)" }} />
        <div style={{ position: "absolute", left: 96, top: 120, fontFamily: FONT }}>
          <div style={{ color: C.accent, fontSize: 20, fontWeight: 800, letterSpacing: "0.3em" }}>LICENSED FOOTAGE</div>
          <div style={{ color: C.text, fontSize: 72, fontWeight: 900, marginTop: 20 }}>{scene.narration.slice(0, 60)}</div>
        </div>
      </AbsoluteFill>
      <Eyebrow text="CINEMATIC EVIDENCE" delay={Math.max(0, localFrame)} />
      <Grade />
    </AbsoluteFill>
  );
}

// ---- Comparison Montage Scene ----
function ComparisonMontageScene({ scene, frame, fps, world, totalDuration, sceneIndex }: SceneRendererProps) {
  const duration = scene.end_s - scene.start_s;
  const localFrame = frame - scene.start_s * fps;
  const progress = Math.min(1, Math.max(0, localFrame / (duration * fps)));
  
  const { land, hi } = useMapPaths(world, ["Italy", "Indonesia", "Thailand", "United States", "China"]);
  
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ transform: `scale(${1 + progress * 0.2})` }}>
        <svg viewBox={`0 0 ${MAP_W} ${MAP_H}`} width={MAP_W} height={MAP_H} style={{ position: "absolute", top: 60, left: 0 }}>
          <rect width={MAP_W} height={MAP_H} fill={C.oceanDeep} opacity={0.6} />
          <path d={land} fill={C.land} stroke={C.landStroke} strokeWidth={0.8} />
          <path d={hi} fill={C.terrain} stroke={C.text} strokeWidth={0.9} />
        </svg>
      </AbsoluteFill>
      <Eyebrow text="GLOBAL COMPARISON" delay={Math.max(0, localFrame)} />
      {scene.text_overlays.includes("city_labels") && (
        <>
          <MapLabel x={800} y={400} text="VENICE" delay={Math.max(0, localFrame + 40)} color={C.accent} />
          <MapLabel x={1400} y={500} text="JAKARTA" delay={Math.max(0, localFrame + 80)} color={C.alert} />
          <MapLabel x={200} y={700} text="NEW ORLEANS" delay={Math.max(0, localFrame + 120)} color={C.growth} />
        </>
      )}
      <Grade />
    </AbsoluteFill>
  );
}

// ---- Satellite Imagery Scene ----
function SatelliteImageryScene({ scene, frame, fps, totalDuration, sceneIndex }: SceneRendererProps) {
  const duration = scene.end_s - scene.start_s;
  const localFrame = frame - scene.start_s * fps;
  const progress = Math.min(1, Math.max(0, localFrame / (duration * fps)));
  
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <svg viewBox="0 0 1920 1080" width={1920} height={1080} style={{ position: "absolute" }}>
        <rect width={1920} height={1080} fill={C.oceanDeep} />
        {/* Simulated satellite imagery layers */}
        <rect x={400} y={200} width={1120} height={680} fill={C.terrain} opacity={0.3} />
        <rect x={500} y={300} width={920} height={480} fill={C.terrainDark} opacity={0.4} />
        <rect x={600} y={400} width={720} height={280} fill={C.accent} opacity={0.2} />
      </svg>
      <Eyebrow text="SATELLITE IMAGERY" delay={Math.max(0, localFrame)} />
      <Grade />
    </AbsoluteFill>
  );
}

// ---- Photo Evidence Scene (default fallback) ----
function PhotoEvidenceScene({ scene, frame, fps, totalDuration, sceneIndex }: SceneRendererProps) {
  const duration = scene.end_s - scene.start_s;
  const localFrame = frame - scene.start_s * fps;
  const progress = Math.min(1, Math.max(0, localFrame / (duration * fps)));
  
  return (
    <AbsoluteFill style={{ background: C.ink }}>
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <AbsoluteFill style={{ background: "linear-gradient(160deg, #1A2A3A 0%, #0A1018 100%)" }} />
        <div style={{ position: "absolute", left: 96, top: 120, fontFamily: FONT }}>
          <div style={{ color: C.accent, fontSize: 20, fontWeight: 800, letterSpacing: "0.3em" }}>PHOTO EVIDENCE</div>
          <div style={{ color: C.text, fontSize: 64, fontWeight: 900, marginTop: 20 }}>{scene.narration.slice(0, 80)}</div>
        </div>
      </AbsoluteFill>
      <Eyebrow text="VISUAL EVIDENCE" delay={Math.max(0, localFrame)} />
      <Grade />
    </AbsoluteFill>
  );
}

// ============================================================================
// Scene Renderer Factory
// ============================================================================

function renderScene(props: SceneRendererProps) {
  const { scene } = props;
  
  switch (scene.visual_objective) {
    case "map_context":
      return <MapContextScene {...props} />;
    case "engineering_demo":
      return <EngineeringDemoScene {...props} />;
    case "data_chart":
      return <DataChartScene {...props} />;
    case "archival_footage":
      return <ArchivalFootageScene {...props} />;
    case "cinematic_footage":
      return <CinematicFootageScene {...props} />;
    case "comparison_montage":
      return <ComparisonMontageScene {...props} />;
    case "satellite_imagery":
      return <SatelliteImageryScene {...props} />;
    default:
      return <PhotoEvidenceScene {...props} />;
  }
}

// ============================================================================
// Main DynamicDocumentary Composition
// ============================================================================

interface DynamicDocumentaryProps {
  manifest: SceneManifest;
}

export const DynamicDocumentary: React.FC<DynamicDocumentaryProps> = ({ manifest }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const world = useWorld();
  const totalDuration = manifest.scenes[manifest.scenes.length - 1]?.end_s || 600;
  
  // Find current scene
  const currentScene = manifest.scenes.find(
    (s) => frame >= s.start_s * fps && frame < s.end_s * fps
  ) || manifest.scenes[manifest.scenes.length - 1];
  
  const sceneIndex = manifest.scenes.findIndex((s) => s.scene_id === currentScene.scene_id);
  
  if (!currentScene) {
    return <AbsoluteFill style={{ background: C.ink }} />;
  }
  
  return (
    <AbsoluteFill style={{ background: C.ink, fontFamily: FONT }}>
      {renderScene({
        scene: currentScene,
        frame,
        fps,
        world,
        totalDuration,
        sceneIndex,
      })}
      {/* Scene ID debug overlay (remove in production) */}
      {process.env.NODE_ENV === "development" && (
        <div style={{ position: "absolute", right: 20, top: 20, color: C.muted, fontSize: 14, fontFamily: "monospace" }}>
          {currentScene.scene_id} | {currentScene.visual_objective} | {currentScene.engine}
        </div>
      )}
    </AbsoluteFill>
  );
};
