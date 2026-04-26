# UI/UX System — Visual & Interaction Guidelines

---

## Design Objective

Create a **premium, cinematic, high-trust interface** suitable for a professional operations platform.

The UI should feel:

* refined
* intentional
* high-end
* minimal but expressive

Avoid generic SaaS styling.

---

## Color System (Instruction-Driven)

### Step 1 — Reference Extraction

Before implementing colors:

* Identify **two high-end, modern product websites**
* Extract:

  * primary accent color
  * background tones
  * text hierarchy colors
  * interaction states (hover, active)

### Step 2 — Palette Construction

Build a palette with:

* **Primary Accent**

  * used for CTAs, highlights, focus states
  * should feel premium (not loud)

* **Dark Surface Tone**

  * deep, rich base for contrast sections
  * slightly tinted (not pure black)

* **Light Surface**

  * warm, soft background (not pure white)

* **Text Colors**

  * primary (high contrast)
  * secondary (muted)
  * disabled (low contrast)

### Rules

* No harsh contrasts
* No neon tones
* No random colors
* Maintain consistency across all components

---

## Visual Style

### Core Aesthetic

* Minimalist
* Architectural
* Editorial layout influence
* Strong alignment and spacing

---

## Glassmorphism (Controlled Usage)

### Guidelines

* Use **subtle transparency**, not heavy blur everywhere
* Apply glass only where:

  * layering is needed
  * emphasis is required

### Properties

* soft background transparency
* light blur
* thin borders

### Avoid

* stacking multiple glass layers unnecessarily
* reducing readability

---

## Typography

### System

* **Headings**

  * elegant serif or refined display font
  * large, expressive, spaced

* **Body**

  * clean sans-serif
  * high readability

---

### Rules

* limit font combinations (max 2)
* avoid excessive weights
* maintain hierarchy clearly

---

## Layout

### Grid

* 8px spacing system
* strong alignment
* predictable structure

---

### Structure

* clear section separation
* generous whitespace
* no visual clutter

---

### Responsiveness

* fluid scaling (prefer clamp())
* avoid heavy breakpoint logic
* consistent experience across screen sizes

---

## Interaction & Motion

### Principles

* subtle
* smooth
* purposeful

---

### Motion Patterns

* fade + slight translate
* soft hover transitions
* minimal scale on interaction

---

### Feedback

* immediate response to user action
* no abrupt jumps

---

## Components

### Buttons

* primary: accent color
* secondary: minimal / outlined / glass
* hover:

  * slight glow or emphasis
  * no aggressive animation

---

### Cards

* clean surfaces or light glass
* subtle borders
* consistent padding

---

### Forms

* minimal inputs
* clear labels
* strong focus states
* no unnecessary decoration

---

## UX Principles

### Clarity

* every action must be obvious
* avoid hidden flows

---

### Guidance

* guide user through steps
* reduce decision fatigue

---

### Visibility

* always show:

  * status
  * progress
  * outcomes

---

## Restrictions

Do NOT:

* use random colors
* overuse animation
* mix multiple visual styles
* create cluttered layouts
* introduce inconsistent spacing

---

## Final Goal

The interface should feel:

* premium
* calm
* precise
* trustworthy

A tool that feels:
→ professionally built
→ visually intentional
→ easy to operate
