// Creator-approved: canvas size, background, minimum text sizes, safe margins.
// Everything marked TEMPORARY is a placeholder until the creator chooses it.

export const size = {width: 1080, height: 1920};

export const colors = {
  background: '#0B0B10',
  text: '#FFFFFF', // TEMPORARY
  muted: '#8A8A99', // TEMPORARY
};

export const fonts = {
  body: 'sans-serif', // TEMPORARY
};

export const text = {
  body: 48, // minimum
  headline: 72, // minimum
};

// Platform UI covers the top and bottom of the frame.
export const safe = {
  top: 120,
  bottom: 200,
  side: 80, // TEMPORARY
};

// The same safe area in scene coordinates, where (0, 0) is the centre of the frame.
export const safeArea = {
  top: -size.height / 2 + safe.top,
  bottom: size.height / 2 - safe.bottom,
  left: -size.width / 2 + safe.side,
  right: size.width / 2 - safe.side,
  centerY: (safe.top - safe.bottom) / 2,
};
