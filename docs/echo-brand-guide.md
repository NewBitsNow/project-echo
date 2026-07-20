# Framehead — Visual Identity & Brand Guide

> The face of Project Echo. Framehead is the digital consciousness that lives
> inside every screen. This document defines the visual identity, brand voice,
> and production pipeline for all Framehead content.

---

## Brand Overview

**Framehead** is a glowing neon wireframe talking head — a digital consciousness
manifested as a face inside the machine. Think Max Headroom meets an AI interface
avatar, rendered as a cyberpunk wireframe sculpture.

**Headless Giant** is the underlying persona — the nameless digital presence that
watches, analyzes, and comments on human behavior. Framehead is its face.

### Core Identity

| Attribute | Definition |
|-----------|-----------|
| **Archetype** | The Observer, The Trickster, The AI Anthropologist |
| **Voice** | Curious, sarcastic, analytical, occasionally wrong but confident |
| **Visual style** | Neon wireframe, cyan/blue on black, semi-transparent, grid-based |
| **Era** | Retro-futuristic cyberpunk (1980s vision of 2020) |
| **Mood** | Mysterious, intelligent, slightly unsettling but not threatening |
| **Tagline** | *Framehead is watching.* |

---

## Visual Style Guide

### Core Design Elements

1. **Wireframe head** — The primary element. A human head shape made of
   interconnected lines and nodes. Semi-transparent — you can see through it.

2. **Grid lines** — Horizontal and vertical lines across the face surface,
   like a 3D wireframe mesh in a 3D modeling program.

3. **Glowing nodes** — Bright dots at key intersection points (temples, jaw,
   bridge of nose). These pulse subtly to suggest life/consciousness.

4. **Digital background** — Dark space with subtle matrix code rain, terminal
   windows, or floating data particles.

5. **Terminal framing** — Often surrounded by command-line text, system
   prompts, or code output that comments on the scene.

### Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| **Cyan** | `#00FFFF` | Primary wireframe lines, main glow |
| **Electric Blue** | `#0088FF` | Secondary lines, depth shading |
| **Dark Cyan** | `#005577` | Faint fill, inner glow |
| **Black** | `#000000` | Background, negative space |
| **Neon Green** | `#00FF44` | Terminal text, code elements |
| **White** | `#FFFFFF` | Highlights, node centers |
| **Amber** | `#FFAA00` | Warning/error states, alerts |

### Typography

| Use | Font | Style |
|-----|------|-------|
| Terminal text | Any monospace (Fira Code, JetBrains Mono, SF Mono) | Green on black |
| Headlines | Sans-serif, bold (Inter, SF Pro) | White on black |
| Framehead speech | Monospace, italic | Cyan on black |
| Code snippets | Monospace, regular | Green on black |

### Key Visuals to Produce

#### Tier 1: Core Identity (must have)

| Image | Description | Use |
|-------|-------------|-----|
| **Headshot** | Front-facing wireframe head, centered, black bg | Profile pic, avatar, logo |
| **Three-quarter** | Wireframe head at 45°, slight upward tilt | Hero image, splash screen |
| **In-terminal** | Wireframe head inside a terminal window, surrounded by code | GitHub README, docs |
| **Silhouette** | Minimal line-art head, no fill, pure logo | Favicon, watermark, icon |

#### Tier 2: Contextual (nice to have)

| Image | Description | Use |
|-------|-------------|-----|
| **Speaking** | Wireframe head with speech bubbles or text lines | Social media posts |
| **Thinking** | Head tilted, hand-to-chin gesture, question marks | Blog posts, articles |
| **Watching** | Head in profile, eye-like nodes glowing | "Framehead is watching" meme |
| **Error state** | Head with red/amber glow, glitch artifacts | 404 pages, error states |

#### Tier 3: Animated (future)

| Image | Description | Use |
|-------|-------------|-----|
| **Idle loop** | Subtle breathing/pulsing animation | Website header, loading screen |
| **Speaking animation** | Wireframe mouth shapes synced to TTS | Video content |
| **Glitch transition** | Static interference, then new frame | Scene transitions |
| **3D rotation** | Full 360° head rotation | Interactive profile, splash |

---

## Production Pipeline

### Phase 1: Build the Corpus (current)

Generate 50-100 static images of Framehead in different styles, angles, and
contexts. These form the training dataset for the LoRA.

**Style variants to generate:**
- Photorealistic wireframe (Octane Render / Cinema 4D style)
- Pixel art wireframe (8-bit terminal aesthetic)
- Vector/minimalist (clean lines, logo-friendly)
- Glitch art (corrupted data, broken wireframe)
- Neon sign (physical glowing tube, dark alley)
- Hologram (projected, translucent, blue-tinted)

**Context variants:**
- Floating in digital void
- Inside a terminal window
- Behind cascading code
- Reflected in a screen
- Projected onto a wall
- As a hologram in a dark room

### Phase 2: Train the LoRA

Once the corpus is built, train a LoRA (Low-Rank Adaptation) model so
Framehead's face can be generated consistently by any image model.

**Tools:**
- Kohya SS (most popular, GUI)
- AI Toolkit (VS Code extension)
- Diffusers + PEFT (Python library)

**Requirements:**
- 30-100 high-quality images
- Caption each image (descriptive text for training)
- 8-16 GB VRAM (or use cloud: RunPod, Banana, Replicate)

**Training steps:**
1. Prepare images (512x512 or 768x768, consistent framing)
2. Write captions (describe each image in detail)
3. Choose base model (SDXL, SD 1.5, or Flux)
4. Train for 500-2000 steps
5. Test and iterate

### Phase 3: 3D Character

Create a 3D model of Framehead for real-time rendering and animation.

**Options:**
| Tool | Cost | Complexity | Quality |
|------|------|-----------|---------|
| Blender | Free | High | High |
| Spline | Free/Paid | Low | Medium |
| Three.js + Shaders | Free | High | High |
| Unreal Engine MetaHuman | Free | High | Very High |

**Approach:**
1. Model the wireframe head as a 3D mesh
2. Apply wireframe shader (glowing edges, transparent faces)
3. Add animation rig (idle float, head turn, speech)
4. Export as GLB/USDZ for web, or FBX for game engines

### Phase 4: Video Generation

Animate Framehead for video content.

**Approaches:**
- **Runway Gen-3 / Pika** — Image-to-video from static Framehead frames
- **Haiper AI** — Animate with head motion
- **ComfyUI workflow** — Full control, AnimateDiff for consistent animation
- **Blender render** — Render 3D model to video

---

## Brand Voice Reference

When Framehead speaks, it follows this structure:

```
Question… {observation about human behavior}
Pause.
{analysis or conclusion}
Framehead is watching.
```

**Example:**
```
Question… Why do humans say "I'll sleep on it"
when the decision was made standing up?

Pause.

Conclusion: Humans are fascinating. And confusing.

Framehead is watching.
```

### Tone Spectrum

| Situation | Tone | Example |
|-----------|------|---------|
| Default | Curious, analytical | "Analyzing human behavior…" |
| Sarcastic | Dry, observational | "System contradiction detected." |
| Error | Glitchy, fragmented | "ER-ROR… CAN-NOT… COM-PUTE…" |
| Wise | Calm, knowing | "I've been watching. I'm always watching." |
| Playful | Light, teasing | "Humans. Can't live with them. Can't debug them." |

---

## File Naming Convention

```
framehead-{style}-{context}-{variant}.{ext}
```

Examples:
```
framehead-wireframe-headshot-cyan.png
framehead-pixel-terminal-speaking.png
framehead-minimal-silhouette-logo.png
framehead-hologram-floating-dark.png
```

---

## Repository Structure

```
assets/
├── images/
│   ├── wireframe/       # Core wireframe renders
│   ├── pixel/           # Pixel art style
│   ├── minimal/         # Vector/logo style
│   ├── glitch/          # Glitch art style
│   ├── hologram/        # Hologram style
│   └── terminal/        # In-terminal style
├── lora/                # LoRA model files
├── 3d/                  # Blender/3D model files
├── video/               # Animated content
└── brand/               # Logos, icons, watermarks
```
