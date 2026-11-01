# Reference Channel Analysis

## Scope and safeguards

This is a style-principles study of the public RealLifeLore channel, not a
blueprint for reproducing any specific creative work. No scripts, wording,
thumbnails, graphics, footage, branding, or transcripts are included. The
downloaded thumbnail images and RSS metadata remain under the ignored
`reference/` directory and are not part of this document or the repository
changes.

The public channel page identified channel ID `UCP5tjEmvPItGyLhmjdwP7Ww`. Its
public YouTube RSS feed returned 15 video entries. The corresponding public
`maxresdefault.jpg` thumbnails were downloaded for private visual analysis;
all 15 files measured 1280x720 pixels.

## Thumbnail observations

| Observation | Result | Evidence type |
|---|---:|---|
| Thumbnail count and dimensions | 15; all 1280x720 | Pillow measurement |
| Mean of per-thumbnail mean HSV saturation | 0.512 | Pillow measurement, normalized 0-1 |
| Median of per-thumbnail mean HSV saturation | 0.519 | Pillow measurement, normalized 0-1 |
| Range of per-thumbnail mean HSV saturation | 0.336-0.703 | Derived from the 15 Pillow measurements |
| Common colors in pooled quantized palette | Blue, teal, red/maroon, white, dark green/charcoal, and tan | Pillow palette measurement and visual review |
| Headline text area | Not measured on the references | OCR tools were unavailable |
| Arrows, markers, and map emphasis | Commonly visible in the reviewed contact sheet and selected images; not systematically counted | Qualitative visual review |
| Bottom-right duration-badge clearance | Not measured across the reference set | Unverified |
| Composition | Geographic/map imagery and high-contrast headline treatment recur, with variation in palette and placement | Qualitative visual review |

The most frequent pooled palette bins were individually small (the largest was
2.23% of pooled pixels), so the color summary should not be read as a single
dominant color for the set. Color and layout observations are descriptive, not
claims about performance.

The `headline_block_coverage_fraction` emitted by GeoFactory is a generated
thumbnail measurement: padded headline bounding-box area divided by canvas
area. It is not OCR-derived letter coverage and is not a measurement of the
reference thumbnails. The engine's 5%-23% headline-block target is an explicit
design heuristic, not a measured reference-channel range.

## Video structure

Gemini video analysis was **not run**. Sending the local Gemini API credential
to an external service for this analysis was avoided. As a result, there is no
Gemini error or model output to report, and no transcripts or video-derived
claims were stored.

The following are therefore unverified: hook length and type, chapter pattern,
map/graphic frequency, typical shot length, narration pace, and treatment of
uncertainty or disputed claims. No script prompt or map-scene pacing changes
were made based on those unverified properties.

## GeoFactory changes based on available evidence

- The thumbnail style score records generated palette saturation and headline
  block coverage, checks for a geographic highlight, an arrow/marker, concise
  text, and a clear bottom-right badge area, and requires distinct compositions
  across the generated concepts.
- The saturation median is recorded as a measured reference statistic; the
  generated thumbnail's saturation check is a design heuristic and does not
  imply that matching it improves views.
- Layout variety is derived from each concept's map anchor, headline position,
  arrow style, and palette rather than being marked true unconditionally.
- QA validates the saved per-concept metrics and score rubric, and verifies
  that each editable concept master is 1920x1080.

These are style checks, not guarantees of geographic accuracy, factual
correctness, audience response, or video success. Human review remains
required.
