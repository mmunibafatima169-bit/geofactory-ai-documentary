# Reference style and original design direction

- Reference channel (style inspiration only): RealLifeLore (https://www.youtube.com/@RealLifeLore). We want the same genre and production quality: long-form, map-driven, "Why ...?" curiosity-based geography explainers. We do NOT copy their scripts, wording, thumbnails, graphics, footage, voice, characters, logos or branding. Every video must be original.
- Our channel name is not decided yet. Use a configurable "channel_name" field, default "CHANNEL_NAME_TBD". Never hardcode any real channel's branding.
- Thumbnail patterns seen in the owner's reference screenshot: (1) dark teal ocean with brown terrain map, one coastal strip highlighted red, a curved white arrow, short two-line label in white on black with the key word in red. (2) beige terrain map with white arrows and a cut-out photo with a white border. (3) blue Europe map with large red movement arrows. (4) red and blue split map with a yellow dashed border line and small quoted labels. (5) beige map with one country in bright green and red X markers, 2-word headline. (6) dark 3D satellite-style terrain with a blue water wave, big number plus keyword. (7) red/orange gradient with a short quote headline.
- Design rules: one main subject and one curiosity question, 2-5 words of bold text, saturated red/blue/yellow/green on dark or terrain backgrounds, map as the hero (highlighted region, big arrows, X marks, dashed border lines, small labels), thick sans-serif text in white with black outline or on a black box with one keyword in red or yellow, keep the bottom-right corner free for the duration badge, readable at about 160 px wide.
- Storytelling principles: open with a surprising question in the first 15 seconds; explain "why" through geography (location, terrain, climate, resources, borders, history); show every major claim on a map or chart when it is spoken; chapters go question, context, cause, consequence, bigger picture, conclusion; calm, confident American English with a mix of short and long sentences; state uncertainty and disputed facts honestly.
- Legal rules: no copyrighted cartoon, anime or meme characters, no logos, no real people's photos without a verified licence, no misleading or inflammatory claims, disputed borders need a clear qualification label, and every topic needs an original composition.

## Additional thumbnail style target

The owner wants thumbnails with a map-first, high-saturation, dramatic, instantly readable geography-infographic treatment. Reproduce only these broad design principles; do not replicate a particular channel's existing artwork, layout, or branding:

- Map is the hero: terrain or satellite-style relief background, one highlighted country or region (bright red, green or yellow fill with a glow or outline), contrasting sea color (deep teal or blue).
- Large, thick, curved or straight arrows (white or red with dark outline) that show direction, movement, flow or cause and effect.
- Red X markers, circle markers, dashed yellow border lines, small quoted labels near locations.
- Optional cut-out element on one side: a licensed photo with a white border (only from verified Wikimedia Commons assets), or an original simple illustrated figure or silhouette drawn by our own code. Never use copyrighted, anime, meme or cartoon characters or real people's faces.
- Bold headline of 2-5 words in thick sans-serif, white with a heavy black outline or on a black box, with one keyword in red or yellow. Optional big number plus keyword for scale or disaster topics.
- Strong vignette, depth and lighting so it looks cinematic, not flat.
- Make every thumbnail composition different: vary map crop, arrow layout, colors and text position. Never reuse one template.
- Add a `style_match` score to automatic scoring, checking: map hero present, highlighted region present, at least one arrow, high saturation, short bold text, bottom-right corner clear, readable at 160 px width.
