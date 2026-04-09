import React from 'react'

// Paths
const ICON_SRC     = '/favicon-removebg-preview.png'      // Blue square icon (imagotipo)
const LOGOTYPE_SRC = '/Diseño sin título (2).png'          // Full logo: icon + "tonder" text (black)

// ── Blue square icon mark ────────────────────────────────────────────────────
export function TonderMark({ size = 36 }) {
  return (
    <img
      src={ICON_SRC}
      alt="Tonder"
      width={size}
      height={size}
      style={{
        width: size,
        height: size,
        borderRadius: Math.round(size * 0.26),
        objectFit: 'cover',
        flexShrink: 0,
        display: 'block',
      }}
    />
  )
}

// ── Full logotype: imagotipo + "tonder" wordmark ─────────────────────────────
// onDark=true → inverts black to white (for dark backgrounds)
export function TonderWordmark({ height = 32, onDark = true, style: extraStyle = {} }) {
  return (
    <img
      src={LOGOTYPE_SRC}
      alt="Tonder"
      style={{
        height,
        width: 'auto',
        objectFit: 'contain',
        display: 'block',
        filter: onDark ? 'invert(1)' : 'none',
        flexShrink: 0,
        ...extraStyle,
      }}
    />
  )
}

// ── Compact: blue icon + inverted wordmark side by side ──────────────────────
// Use when you want the colored icon next to the white text logo
export function TonderBrand({ iconSize = 32, logoHeight = 22 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <TonderMark size={iconSize} />
      {/* Only the text part — we crop by using the full logotype but the icon
          in the PNG is the same as the blue favicon, so we just show the logotype inverted */}
      <img
        src={LOGOTYPE_SRC}
        alt="tonder"
        style={{
          height: logoHeight,
          width: 'auto',
          filter: 'invert(1)',
          objectFit: 'contain',
          display: 'block',
        }}
      />
    </div>
  )
}
