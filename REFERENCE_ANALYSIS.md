# Reference Channel Analysis

## Scope and method

This study extracts broad style principles from public RealLifeLore thumbnails
only. It does not reproduce or include any script, wording, thumbnail artwork,
graphic, footage, or branding. No video transcripts or video-structure analysis
were requested or collected.

The public channel page and its public RSS feed were accessible without bypass
or authentication. The feed identified channel ID `UCP5tjEmvPItGyLhmjdwP7Ww`
and returned 15 recent entries. All 15 public
`img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg` thumbnails downloaded
successfully. `reference/` was ignored by Git before downloads; the images,
RSS listing, contact sheet, and per-image measurements remain private there.

Pillow measured dimensions, HSV saturation, and quantized colors. All 15 images
were reviewed in a contact sheet; five were also opened at full resolution.
OCR was unavailable. For text area, a reviewer visually annotated approximate
headline/callout bounding boxes, and Pillow calculated their pixel-area share.
Thus, text-area values are **manual bounding-box estimates**, not OCR, exact
letter-pixel measurements, or fully automated detection. Arrow/marker and
duration-corner classifications are also visual estimates.

## Thumbnail findings

| Observation | Result | Evidence |
|---|---:|---|
| Sample size and dimensions | 15; all 1280×720 | Pillow measurement |
| Mean of per-thumbnail mean HSV saturation | 0.5124 | Pillow, normalized 0–1 |
| Median of per-thumbnail mean HSV saturation | 0.5194 | Pillow, normalized 0–1 |
| Range of per-thumbnail mean HSV saturation | 0.3361–0.7028 | Pillow, normalized 0–1 |
| Text-bearing headline/callout box area, mean | 9.25% of frame | Pillow area from visually annotated boxes; estimated |
| Text-bearing headline/callout box area, median | 6.70% of frame | Pillow area from visually annotated boxes; estimated |
| Text-bearing headline/callout box area, range | 0–23.82% | Pillow area from visually annotated boxes; estimated |
| Thumbnail with a visible arrow or directional route | 8/15 | Visual classification |
| Thumbnail with a map marker or highlighted region | 12/15 | Visual classification |
| Bottom-right duration-badge area visually clear | 12/15 | Subjective visual classification |
| Distinct broad compositions in the sample | 15/15 | Visual classification; descriptive, not a performance metric |

The ten largest colors in the equally weighted, downsampled pooled palette were:

| Color | Share |
|---|---:|
| `#163E5A` (deep blue) | 13.37% |
| `#090B18` (near-black) | 13.34% |
| `#B89264` (earth tan) | 12.77% |
| `#598C7D` (teal/green) | 10.77% |
| `#E9BE96` (light earth) | 10.45% |
| `#93603A` (brown) | 9.33% |
| `#A3B8A5` (muted green) | 8.64% |
| `#6F2137` (maroon) | 7.82% |
| `#4C574F` (dark green/gray) | 7.46% |
| `#F7EED6` (warm white) | 6.05% |

Palette shares are quantized pixel shares after resizing each source to
160×90, with each thumbnail contributing the same number of pixels. Smaller
bright accents, including red, yellow, and white, also appear in the visual
review but are not among those ten pooled bins.

### Style principles supported by this sample

- Lead with geographic context: map, terrain, satellite-style imagery, or a
  globe is often the largest visual element.
- Use a small number of strongly contrasting map highlights, route lines,
  arrows, markers, or labels to direct attention.
- Keep headline/callout blocks compact relative to the map; preserve a visible
  corner for a duration badge.
- Use varied earth, blue/teal, dark, and occasional saturated accent colors.
- Vary crop, visual balance, headline placement, and annotation layout rather
  than repeating one composition.

These are descriptive principles, not requirements to imitate any reference
thumbnail. Every GeoFactory composition remains original and uses its own
licensed or generated map elements.

## Video structure and other unverified findings

The videos themselves were not analyzed. Hook type or duration, chapter pattern,
map/graphic screen-time share, shot length, narration pace, and treatment of
uncertainty or disputed claims are **unverified**. No Gemini request was made
and no API key was transmitted. Public availability of an API key does not make
video analysis necessary for this thumbnail-only task.

## GeoFactory application

- Thumbnail concept masters are rendered at 3840×2160 (2× supersampling) and
  downsampled to 1920×1080; the selected platform export remains 1280×720.
- Thumbnail geometry uses pinned Natural Earth 1:50m Admin 0 Countries data,
  release 5.1.1. Its public-domain licence, source, download date, and checksum
  are recorded. Map animation scenes continue to use their separate 1:110m data.
- The style rubric uses the observed per-image saturation range and the
  manually estimated 0–23.82% headline/callout-box area range as reference
  bounds. Its generated-thumbnail coverage measurement is still a padded
  headline-box area calculation, not detected text.
- Arrow/marker presence, a clear duration corner, concise headline length, and
  distinct concept layouts are checked as design heuristics.

Scores do not establish geographic or factual accuracy and do not predict
views. Human review remains necessary.
