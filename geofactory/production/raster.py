"""Satellite and DEM array/raster processing. No video rendering functions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, calculate_default_transform, reproject


class RasterProcessingError(ValueError):
    pass


def robust_rgb_stretch(
    red: np.ndarray,
    green: np.ndarray,
    blue: np.ndarray,
    *,
    valid_mask: np.ndarray | None = None,
    lower_percentile: float = 2.0,
    upper_percentile: float = 98.0,
) -> np.ndarray:
    """Return display RGB uint8; preserve source rasters separately."""
    bands = np.stack([red, green, blue]).astype(np.float32)
    if bands.ndim != 3 or bands.shape[0] != 3 or not all(b.shape == bands.shape[1:] for b in (red, green, blue)):
        raise RasterProcessingError("RGB inputs must be three equally sized 2D arrays")
    valid = np.isfinite(bands).all(axis=0) if valid_mask is None else valid_mask.astype(bool) & np.isfinite(bands).all(axis=0)
    if not valid.any():
        raise RasterProcessingError("No valid satellite pixels")
    if not 0 <= lower_percentile < upper_percentile <= 100:
        raise RasterProcessingError("Invalid stretch percentiles")
    output = np.zeros(bands.shape, dtype=np.uint8)
    for index in range(3):
        values = bands[index][valid]
        low, high = np.percentile(values, [lower_percentile, upper_percentile])
        if high <= low:
            low, high = float(values.min()), float(values.max())
        scaled = np.zeros_like(bands[index], dtype=np.float32) if high <= low else np.clip((bands[index] - low) / (high - low), 0, 1)
        output[index] = np.rint(scaled * 255).astype(np.uint8)
    return output


def cloud_valid_mask(qa60: np.ndarray) -> np.ndarray:
    """Sentinel-2 QA60: bits 10/11 are opaque/cirrus clouds."""
    qa = np.asarray(qa60)
    if qa.ndim != 2:
        raise RasterProcessingError("QA60 must be a 2D array")
    return (qa & (1 << 10) == 0) & (qa & (1 << 11) == 0)


def decode_terrarium(red: np.ndarray, green: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Decode Mapzen Terrarium PNG elevation in metres."""
    arrays = [np.asarray(channel) for channel in (red, green, blue)]
    if any(channel.ndim != 2 or channel.shape != arrays[0].shape for channel in arrays):
        raise RasterProcessingError("Terrarium channels must be equally sized 2D arrays")
    return arrays[0].astype(np.float64) * 256 + arrays[1].astype(np.float64) + arrays[2].astype(np.float64) / 256 - 32768


def hillshade(elevation: np.ndarray, cell_size: float, azimuth_deg: float = 315, altitude_deg: float = 45) -> np.ndarray:
    """Compute uint8 hillshade with geographic-unaware grid inputs rejected."""
    dem = np.asarray(elevation, dtype=np.float64)
    if dem.ndim != 2 or min(dem.shape) < 3 or cell_size <= 0:
        raise RasterProcessingError("Hillshade needs a >=3x3 DEM and positive cell size")
    if not 0 <= azimuth_deg <= 360 or not 0 < altitude_deg <= 90:
        raise RasterProcessingError("Invalid sun angles")
    dy, dx = np.gradient(dem, cell_size, cell_size)
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    azimuth = np.deg2rad(360 - azimuth_deg + 90)
    altitude = np.deg2rad(altitude_deg)
    shaded = np.sin(altitude) * np.cos(slope) + np.cos(altitude) * np.sin(slope) * np.cos(azimuth - aspect)
    return np.rint(np.clip(shaded, 0, 1) * 255).astype(np.uint8)


def reproject_dem(source: Path, destination: Path, target_crs: str, resolution: float | None = None) -> dict:
    """Reproject a DEM with bilinear resampling and preserve a vertical datum note."""
    with rasterio.open(source) as src:
        if src.crs is None or src.count != 1:
            raise RasterProcessingError("DEM needs one band and a declared CRS")
        transform, width, height = calculate_default_transform(src.crs, target_crs, src.width, src.height, *src.bounds, resolution=resolution)
        profile = src.profile.copy()
        profile.update(crs=target_crs, transform=transform, width=width, height=height, compress="deflate")
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(destination, "w", **profile) as dst:
            reproject(source=rasterio.band(src, 1), destination=rasterio.band(dst, 1), src_transform=src.transform, src_crs=src.crs, src_nodata=src.nodata, dst_transform=transform, dst_crs=target_crs, dst_nodata=src.nodata, resampling=Resampling.bilinear)
        vertical_datum = src.tags().get("vertical_datum", "UNDECLARED — review required")
    return {"target_crs": target_crs, "width": width, "height": height, "vertical_datum": vertical_datum, "interpolation": "bilinear"}
