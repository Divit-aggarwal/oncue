// Single source of truth for every visual value. Creator-approved 2026-09-17.

export const size = {width: 1080, height: 1920};

export const colors = {
  bg: '#0B0B10',
  text: '#F5F5F7',
  muted: '#8E8E9A',
  accent: '#7F77DD',
  accent2: '#4FC3D9',
  success: '#4CC38A',
  danger: '#E5484D',
};

export const font = {family: 'Inter', regular: 400, bold: 700};

// Body text never below 48px, headlines never below 72px.
export const type = {headline: 120, body: 56, caption: 48};

export const space = {xs: 16, sm: 32, md: 64, lg: 120};

export const radius = 24;
export const stroke = 4;

export const duration = {fast: 0.3, normal: 0.6, slow: 1};

// Platform UI covers the top and bottom of the frame.
export const safe = {top: 120, bottom: 200, side: 80};

// The safe area in scene coordinates, where (0, 0) is the centre of the frame.
export const safeArea = {
  top: -size.height / 2 + safe.top,
  bottom: size.height / 2 - safe.bottom,
  left: -size.width / 2 + safe.side,
  right: size.width / 2 - safe.side,
  centerY: (safe.top - safe.bottom) / 2,
};
