# Composition skeleton

Four pieces carry almost every scene: a sizing unit, a theme block, a safe area, and
two animation helpers. Write them once and the scenes stay short.

## One sizing unit

The canvas is a fixed 1920 x 1080, so pick a unit that is a share of the width and
express every size in it. The whole layout then keeps its proportions if you change
the resolution, and the same numbers work in an HTML version of the same design.

```ts
/** One percent of the video width. */
export const u = (pct: number) => pct * 19.2;
```

Use it everywhere: `fontSize: u(4.2)`, `gap: u(1.5)`, `padding: u(1.8)`.

## Theme

Keep every colour and font in one file so a restyle is one edit.

```ts
import { loadFont as loadDisplay } from "@remotion/google-fonts/<DisplayFamily>";
import { loadFont as loadMono } from "@remotion/google-fonts/<MonoFamily>";

// Name the weights and the subset. Without arguments, loadFont() fetches every
// weight and every subset the family has, which is roughly a hundred requests.
const display = loadDisplay("normal", { weights: ["600", "700"], subsets: ["latin"] });
const mono = loadMono("normal", { weights: ["400"], subsets: ["latin"] });

export const DISPLAY = display.fontFamily;
export const MONO = mono.fontFamily;

export const C = {
  bg: "#...", panel: "#...", line: "#...",
  fg: "#...", muted: "#...", dim: "#...",
  accent: "#...",   // the one thing the video is about
  ok: "#...", neg: "#...",
} as const;

/**
 * Long identifiers are a single word to the line breaker, so it splits them at an
 * arbitrary letter. A zero-width space after each separator offers a sensible place.
 */
export const soft = (s: string) => s.replace(/([_/])/g, "$1​");
```

Pick a different palette and a different type pairing for each subject. A video that
looks like the last one carries less than one that looks like its own topic.

## Safe area

Anything drawn in the corners (a label, a scene counter) will collide with scene
content unless every scene keeps clear of it. Apply one wrapper in the composition
rather than padding in each scene.

```tsx
export const Stage: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{
    position: "absolute", inset: 0,
    padding: `${u(8)}px ${u(6)}px`,
    display: "flex", flexDirection: "column", justifyContent: "center",
    boxSizing: "border-box",
  }}>{children}</div>
);
```

## Two animation helpers

`Reveal` lifts a block into place, `Pop` grows it. `delay` is in frames. Between them
they cover nearly every entrance; reach for anything else only when a scene asks for
it.

```tsx
export const Reveal: React.FC<{ delay?: number; y?: number; children: React.ReactNode }> =
  ({ delay = 0, y = u(1.6), children }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();
    const p = spring({ frame: frame - delay, fps,
                       config: { damping: 200, mass: 0.6 }, durationInFrames: 18 });
    return <div style={{ opacity: p, transform: `translateY(${(1 - p) * y}px)` }}>{children}</div>;
  };
```

`spring()` returns 0 while `frame - delay` is negative, so a delayed element simply
stays hidden until its moment. No conditional rendering is needed.

## Scenes in order

```tsx
import data from "./scenes.json";

const BODIES = [S1, S2, S3 /* one component per narration file, same order */];
const LEAD_FRAMES = Math.round(data.lead * data.fps);
export const TOTAL_FRAMES = data.scenes.reduce((a, s) => a + s.durationInFrames, 0);

export const Video: React.FC = () => (
  <AbsoluteFill style={{ background: C.bg }}>
    <Backdrop />
    <Series>
      {data.scenes.map((s, i) => {
        const Body = BODIES[i];
        return (
          <Series.Sequence key={s.id} durationInFrames={s.durationInFrames} name={s.label}>
            {/* the audio must sit inside its own scene, or it plays over the wrong one */}
            <Sequence from={LEAD_FRAMES} name="narration">
              <Audio src={staticFile(s.audio)} />
            </Sequence>
            <AbsoluteFill>
              <Stage><Body /></Stage>
              <Hud index={s.id} total={data.scenes.length} label={s.label} />
            </AbsoluteFill>
          </Series.Sequence>
        );
      })}
    </Series>
  </AbsoluteFill>
);
```

Register it with the total length taken from the same file:

```tsx
<Composition id="<COMPOSITION_ID>" component={Video}
             durationInFrames={TOTAL_FRAMES} fps={FPS} width={1920} height={1080} />
```

## Timing a scene against its narration

`scenes.json` records how long each scene speaks. Place the reveals inside that
window by ear: read the narration, estimate which second each sentence starts, and
multiply by the frame rate. A delay of `150` at 30 frames per second means the
element appears five seconds into the scene, half a second after the voice has
started (the lead-in).

Exact word-level synchronisation needs a forced aligner and is rarely worth it. Being
within half a second reads as deliberate.

## Drawing the subject's own mechanism

One custom drawing is usually worth more than five more bullet lists: the thing the
work is actually about, drawn and animated. Derive its state from the frame number so
it stays reproducible:

```tsx
const step = Math.round(interpolate(frame, [from, to], [0, totalSteps],
  { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
```

Then draw the state at `step`. No timers, no animation state, and any frame can be
rendered on its own — which is what makes a single-frame still check possible.
