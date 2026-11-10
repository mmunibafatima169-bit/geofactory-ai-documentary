/**
 * Shared documentary design system.
 * Mirrors geofactory/studio/design_tokens.py — keep both in sync.
 */
export const C = {
  ink: "#0A1018",
  panel: "#121C28",
  ocean: "#163E5A",
  oceanDeep: "#0E2A3E",
  land: "#22384E",
  landStroke: "#3A4E66",
  terrain: "#B89264",
  terrainDark: "#93603A",
  accent: "#F2C14E",
  alert: "#E23A2E",
  growth: "#598C7D",
  text: "#F5F1E8",
  muted: "#8B94A3",
  hairline: "#2E3E54",
} as const;

export const FONT = "DejaVu Sans, sans-serif";

export const VENICE: [number, number] = [12.3371, 45.4371];

/** Equirectangular projection helpers for the Natural Earth world map. */
export const MAP_W = 1920;
export const MAP_H = 960;

export const project = (lon: number, lat: number): [number, number] => [
  ((lon + 180) / 360) * MAP_W,
  ((90 - lat) / 180) * MAP_H,
];

export interface Feature {
  properties: { NAME_EN?: string; NAME?: string; [k: string]: unknown };
  geometry: { type: string; coordinates: unknown };
}

export function featureToPath(f: Feature): string {
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
