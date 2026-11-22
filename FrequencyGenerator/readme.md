# Tone Generator

A single-file browser tone generator that plays a continuous tone anywhere from 20 Hz to 20 kHz, with a live oscilloscope. It has no dependencies and makes no network requests. It uses the Web Audio API, so it runs in any modern desktop or mobile browser.

## Running it

Open the HTML file in a browser and press **Start tone**. No server or build step is needed. Audio only starts after you click or tap, because browsers block sound that starts on its own.

## Controls

**Frequency**
- **Number box:** type any value from 20 to 20,000 Hz. Valid values apply as you type. When you leave the box, an out-of-range value is clamped to the nearest limit, and an empty or invalid entry reverts to the current frequency.
- **Slider:** a logarithmic scale, so equal distances on the slider are equal musical intervals, with about 0.7% per step. Low frequencies get as much room as high ones.
- **Step buttons (−10, −1, +1, +10):** nudge the frequency by whole hertz. The current value is rounded to a whole number first.
- **Presets:** 50 Hz, 100 Hz, 440 Hz, 1k, 5k, 10k, 15k and 20k.
- **Range label:** under the number, a short description of the current band, from "Sub-bass" through "Bass", "Midrange" and "Presence" to "Air".

**Playback**
- **Start tone / Stop tone** button, or press **Space** when no input, menu or button has focus.
- **Waveform:** sine, square, triangle or sawtooth. It can be changed while playing.
- **Volume:** 0 to 100%, default 20%. The slider is squared and scaled so the loudest setting is half of full output, which gives finer control at low levels.

**Oscilloscope**
- Shows about three cycles of the live waveform, triggered on a rising zero crossing so the trace stays steady.
- The trace is scaled to the volume setting. It is a flat line when the tone is stopped.

## Behavior details

- **Smooth changes:** frequency changes glide over a few milliseconds, and the volume fades in and out over about 20 ms. This avoids clicks when you drag the slider or start and stop the tone.
- **Appearance:** it follows your system light or dark setting. Setting `data-theme="light"` or `data-theme="dark"` on the root element overrides this.
- **Mobile:** it respects safe-area insets on notched phones. The controls are sized for touch.
- **Accessibility:** the controls have labels, the play button reports its pressed state, and focus outlines are visible.

## Customizing

All the settings are near the top of the script or in short lists:

| To change | Edit |
|---|---|
| Frequency range | `MIN` and `MAX` (also the `min` and `max` on the number input) |
| Preset buttons | The array of `[hertz, label]` pairs near the end of the script |
| Range descriptions | The `describe()` function |
| Maximum loudness or volume curve | `level()` |
| Smoothing speed | The time constants in `setTargetAtTime` calls |

## Known quirks

- The tick labels under the slider (20, 100, 1k, 10k, 20k) are evenly spaced, but the slider is logarithmic, so they only roughly line up with where those frequencies sit.
- The tone keeps playing if you switch tabs. The `visibilitychange` listener is empty, so nothing happens there. Browsers may throttle or suspend audio in background tabs.
- Typing a value below 20 or above 20,000 does not change the tone until you leave the box.
- Small speakers and headphones reproduce very little below about 100 Hz, and many adults hear little above 15 kHz. A quiet tone at the extremes may be inaudible even though it is playing.

## Safety

Start with your device volume low. Very high and very low tones, and square or sawtooth waves in particular, can be harsh on speakers and hearing. The page shows the same warning on screen.
