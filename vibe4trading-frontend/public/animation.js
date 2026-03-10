(() => {
  const SETTINGS = {
  "charset": "standard",
  "customCharset": " .:-=+*#%@",
  "brailleVariant": "standard",
  "fontSize": 10,
  "hoverStrength": 24,
  "mouseInteractionMode": "attract",
  "mouseAreaSize": 180,
  "mouseSpread": 1,
  "charSpacing": 1,
  "renderFont": "\"Helvetica Neue\", Helvetica, Arial, sans-serif",
  "outputAspect": "4:3",
  "contrast": 2,
  "brightness": -14,
  "opacity": 1,
  "vignette": 0,
  "borderGlow": 0,
  "bgDither": 0.45,
  "inverseDither": 0,
  "invert": false,
  "ditherType": "floyd-steinberg",
  "ditherStrength": 0.75,
  "style": "classic",
  "halftoneShape": "circle",
  "halftoneSize": 1,
  "halftoneRotation": 0,
  "colorMode": "grayscale",
  "terminalCharset": "binary",
  "retroDuotone": "amber-classic",
  "retroNoise": 0.45,
  "backgroundColor": "#000000",
  "customColor": "#00ff99",
  "particleDensity": 0.5,
  "particleChar": "*",
  "letterSet": "alphabet",
  "claudeDensity": 0.7,
  "lineLength": 1,
  "lineWidth": 1,
  "lineThickness": 1.6,
  "lineRotation": 0,
  "overlayPreset": "noise",
  "overlayStrength": 0.45,
  "noiseScale": 24,
  "noiseSpeed": 1,
  "noiseDirection": "right",
  "intervalSpacing": 12,
  "intervalSpeed": 1,
  "intervalWidth": 2,
  "intervalDirection": "down",
  "beamDirection": "right",
  "glitchDirection": "right",
  "crtDirection": "down",
  "matrixDirection": "down",
  "matrixScale": 18,
  "matrixSpeed": 1
};
  const EXPORT_OPTIONS = {"enableInteractionEffects":true,"transparentBackground":true,"enableAlphaMask":true,"alphaMaskEnd":85,"enableFadeIn":true,"fadeInDurationMs":900,"pauseWhenOffscreen":true,"adaptivePerformance":true,"maxFps":30,"idleFps":12,"visibilityThreshold":0.01,"reportFps":false,"enableWatermark":false,"watermarkText":"Made in ASC11"};
  const SOURCE = {
  "type": "image",
  "url": "data:image/jpeg;base64,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"
};
  const IS_TRANSPARENT_BG = Boolean(EXPORT_OPTIONS.transparentBackground);
  const WATERMARK_LABEL = String(EXPORT_OPTIONS.watermarkText || "Made in ASC11");

  const CHARSETS = {"standard":" .:-=+*#%@","blocks":" ░▒▓█","detailed":" .'`^\",:;Il!i><~+_-?][}{1)(|\\\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$","minimal":" ·░█","binary":" 01","letters-alphabet":"ABCDEFGHIJKLMNOPQRSTUVWXYZ","letters-lowercase":"abcdefghijklmnopqrstuvwxyz","letters-mixed":"AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz","letters-symbols":"@#$%&*+=-<>~","braille":" ⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿"};
  const BRAILLE_VARIANTS = {"standard":" ⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿","sparse":" ⠁⠂⠄⠈⠐⠠⡀⢀⣀⣿","dense":" ⠃⠇⠏⠟⠿"};
  const MATRIX_CHARS = " アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン";
  const HALFTONE_CHARS = " .,:;irsXA253hMHGS#9B&@";
  const RETRO_CHARS = "o";
  const TERMINAL_CHARSET_PRESETS = {"binary":" 010101","brackets":" []/\\<>","symbols":" $_+","mixed":" 01[]/\\<>$_+|","matrix":" 01{}[]/\\<>|_+-"};
  const RETRO_DUOTONE_PALETTES = {"amber-classic":{"low":{"r":20,"g":12,"b":6},"high":{"r":255,"g":223,"b":178}},"cyan-night":{"low":{"r":6,"g":16,"b":22},"high":{"r":166,"g":240,"b":255}},"violet-haze":{"low":{"r":17,"g":10,"b":26},"high":{"r":242,"g":198,"b":255}},"lime-pulse":{"low":{"r":10,"g":18,"b":8},"high":{"r":226,"g":255,"b":162}},"mono-ice":{"low":{"r":12,"g":12,"b":12},"high":{"r":245,"g":248,"b":255}}};
  const HOVER_ATTRACT_RADIUS = 180;
  const CLICK_BURST_RADIUS = 340;
  const CLICK_BURST_STRENGTH = 56;
  const CLICK_BURST_DURATION_MS = 640;
  const FPS_MESSAGE_TYPE = "ascii-dither-template-fps";
  const IS_TEMPLATE_PREVIEW_RUNTIME = EXPORT_OPTIONS.reportFps === true;
  const TEMPLATE_PREVIEW_RUNTIME_KEY = '__asciiTemplatePreviewRuntime__';
  const runtimeScope = typeof window !== 'undefined' ? window : globalThis;
  const previewRuntimeId = IS_TEMPLATE_PREVIEW_RUNTIME ? String(Date.now()) + '-' + Math.random().toString(36).slice(2) : '';
  const SHOULD_REPORT_FPS =
    EXPORT_OPTIONS.reportFps === true &&
    typeof window.parent !== 'undefined' &&
    window.parent !== window;

  if (IS_TEMPLATE_PREVIEW_RUNTIME) {
    const existingRuntime = runtimeScope[TEMPLATE_PREVIEW_RUNTIME_KEY];
    if (existingRuntime && typeof existingRuntime.destroy === 'function') {
      try {
        existingRuntime.destroy();
      } catch {
        // Ignore stale runtime destroy errors.
      }
    }
    runtimeScope[TEMPLATE_PREVIEW_RUNTIME_KEY] = { id: previewRuntimeId, destroy: null };
  }

  const mount = document.querySelector('[data-ascii-dither-bg]');
  if (!mount) return;

  if (typeof mount.__asciiDitherDestroy === 'function') {
    mount.__asciiDitherDestroy();
  }

  mount.style.position = 'absolute';
  mount.style.inset = '0';
  mount.style.top = '0';
  mount.style.left = '0';
  mount.style.right = '0';
  mount.style.bottom = '0';
  mount.style.height = '100%';
  mount.style.zIndex = '0';
  mount.style.pointerEvents = 'none';
  mount.style.overflow = 'hidden';
  mount.style.background = 'transparent';
  const fadeInDurationMs = Math.max(0, Number(EXPORT_OPTIONS.fadeInDurationMs ?? 900) || 900);
  if (EXPORT_OPTIONS.enableFadeIn === true && fadeInDurationMs > 0) {
    mount.style.opacity = '0';
    mount.style.transition = 'opacity ' + fadeInDurationMs + 'ms ease';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        mount.style.opacity = '1';
      });
    });
  } else {
    mount.style.opacity = '1';
    mount.style.removeProperty('transition');
  }

  const parent = mount.parentElement;
  if (parent && window.getComputedStyle(parent).position === 'static') {
    parent.style.position = 'relative';
  }

  const backgroundLayer = document.createElement('div');
  Object.assign(backgroundLayer.style, {
    position: 'absolute',
    inset: '0',
    pointerEvents: 'none',
    zIndex: '0',
    background: IS_TRANSPARENT_BG ? 'transparent' : (SETTINGS.backgroundColor || '#000000')
  });

  const canvas = document.createElement('canvas');
  Object.assign(canvas.style, {
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: 'auto',
    height: 'auto',
    maxWidth: '100%',
    maxHeight: '100%',
    transform: 'translate(-50%, -50%)',
    display: 'block',
    zIndex: '1'
  });
  const legacyAlphaMaskStop = Math.max(0, Math.min(100, Number(EXPORT_OPTIONS.alphaMaskStop ?? 85) || 85));
  const alphaMaskEndRaw = Number(EXPORT_OPTIONS.alphaMaskEnd ?? legacyAlphaMaskStop);
  const alphaMaskEnd = Math.max(0, Math.min(100, Number.isFinite(alphaMaskEndRaw) ? alphaMaskEndRaw : legacyAlphaMaskStop));
  if (EXPORT_OPTIONS.enableAlphaMask !== false) {
    const alphaMaskValue =
      'linear-gradient(to bottom, black 0%, black ' + alphaMaskEnd + '%, transparent 100%)';
    mount.setAttribute('data-alpha-mask', 'bottom-' + alphaMaskEnd);
    canvas.style.setProperty('mask-image', alphaMaskValue);
    canvas.style.setProperty('-webkit-mask-image', alphaMaskValue);
  } else {
    mount.removeAttribute('data-alpha-mask');
    canvas.style.removeProperty('mask-image');
    canvas.style.removeProperty('-webkit-mask-image');
  }

  let watermarkLayer = null;
  if (EXPORT_OPTIONS.enableWatermark === true) {
    watermarkLayer = document.createElement('div');
    Object.assign(watermarkLayer.style, {
      position: 'absolute',
      right: '14px',
      bottom: '12px',
      zIndex: '3',
      pointerEvents: 'none',
      userSelect: 'none',
      font: '600 12px "Helvetica Neue", Helvetica, Arial, sans-serif',
      letterSpacing: '0.03em',
      color: 'rgba(255, 255, 255, 0.92)',
      padding: '4px 8px',
      borderRadius: '999px',
      border: '1px solid rgba(255, 255, 255, 0.24)',
      background: 'rgba(0, 0, 0, 0.5)',
      textShadow: '0 1px 1px rgba(0, 0, 0, 0.45)',
    });
    watermarkLayer.textContent = WATERMARK_LABEL;
  }

  if (watermarkLayer) {
    mount.replaceChildren(backgroundLayer, canvas, watermarkLayer);
  } else {
    mount.replaceChildren(backgroundLayer, canvas);
  }

  const ctx = canvas.getContext('2d');
  const sampleCanvas = document.createElement('canvas');
  const sampleCtx = sampleCanvas.getContext('2d', { willReadFrequently: true });
  if (!ctx || !sampleCtx) throw new Error('Could not create canvas context');

  let source = null;
  let stream = null;
  let sourceLoopHandler = null;
  let rafId = null;
  let intersectionObserver = null;
  let resizeObserver = null;
  let bounds = { left: 0, top: 0, width: 1, height: 1 };
  let viewWidth = 1;
  let viewHeight = 1;
  let renderWidth = 1;
  let renderHeight = 1;
  let pointer = { inside: false, x: 0, y: 0 };
  let clickBursts = [];
  let matrixRainState = { laneCount: 0, primaryCount: 0, speeds: [], phases: [], lengths: [] };
  let isInViewport = true;
  let isPageVisible = document.visibilityState !== 'hidden';
  let pendingForceRender = false;
  let lastRenderTime = 0;
  let fpsFrameCount = 0;
  let fpsWindowStart = 0;
  let lastReportedSignature = '';
  let lastFrameDurationMs = 0;
  let lastCharCount = 0;

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function reportFps(value, details = {}) {
    if (!SHOULD_REPORT_FPS) return;
    const normalized = Math.max(0, Math.round(Number(value) || 0));
    const normalizedChars = Math.max(0, Math.round(Number(details.chars) || 0));
    const normalizedFrameMs = Math.max(0, Math.round((Number(details.frameMs) || 0) * 10) / 10);
    const signature = normalized + '|' + normalizedChars + '|' + normalizedFrameMs;
    if (signature === lastReportedSignature) return;
    lastReportedSignature = signature;
    try {
      window.parent.postMessage(
        {
          type: FPS_MESSAGE_TYPE,
          fps: normalized,
          chars: normalizedChars,
          frameMs: normalizedFrameMs,
          instanceId: previewRuntimeId,
        },
        '*'
      );
    } catch {
      // Ignore cross-frame postMessage errors.
    }
  }

  function getDirectionVector(direction) {
    switch (direction) {
      case 'up':
        return { dx: 0, dy: -1 };
      case 'down':
        return { dx: 0, dy: 1 };
      case 'left':
        return { dx: -1, dy: 0 };
      case 'top-left':
        return { dx: -Math.SQRT1_2, dy: -Math.SQRT1_2 };
      case 'top-right':
        return { dx: Math.SQRT1_2, dy: -Math.SQRT1_2 };
      case 'bottom-left':
        return { dx: -Math.SQRT1_2, dy: Math.SQRT1_2 };
      case 'bottom-right':
        return { dx: Math.SQRT1_2, dy: Math.SQRT1_2 };
      case 'right':
      default:
        return { dx: 1, dy: 0 };
    }
  }

  function getDirectionProjection(direction) {
    const { dx, dy } = getDirectionVector(direction);
    const perpX = -dy;
    const perpY = dx;
    const primaryMin = (dx < 0 ? dx : 0) + (dy < 0 ? dy : 0);
    const primaryMax = (dx > 0 ? dx : 0) + (dy > 0 ? dy : 0);
    const secondaryMin = (perpX < 0 ? perpX : 0) + (perpY < 0 ? perpY : 0);
    const secondaryMax = (perpX > 0 ? perpX : 0) + (perpY > 0 ? perpY : 0);
    return {
      dx,
      dy,
      perpX,
      perpY,
      primaryMin,
      primarySpan: Math.max(0.0001, primaryMax - primaryMin),
      secondaryMin,
      secondarySpan: Math.max(0.0001, secondaryMax - secondaryMin),
    };
  }

  function projectDirection(x, y, cols, rows, projection) {
    const xNorm = x / Math.max(cols - 1, 1);
    const yNorm = y / Math.max(rows - 1, 1);
    const primaryRaw = xNorm * projection.dx + yNorm * projection.dy;
    const secondaryRaw = xNorm * projection.perpX + yNorm * projection.perpY;
    const primaryNorm = clamp((primaryRaw - projection.primaryMin) / projection.primarySpan, 0, 1);
    const secondaryNorm = clamp((secondaryRaw - projection.secondaryMin) / projection.secondarySpan, 0, 1);
    return { primaryNorm, secondaryNorm };
  }

  function applyTone(gray) {
    let value = gray;
    value = (value - 128) * SETTINGS.contrast + 128;
    value += SETTINGS.brightness * 2;
    value = clamp(value, 0, 255);
    if (SETTINGS.invert) value = 255 - value;
    return value;
  }

  function bayerThreshold(x, y) {
    const matrix = [
      [0, 8, 2, 10],
      [12, 4, 14, 6],
      [3, 11, 1, 9],
      [15, 7, 13, 5]
    ];
    return matrix[y % 4][x % 4] / 16;
  }

  function drawRegularPolygon(ctx, centerX, centerY, radius, sides, rotation) {
    if (!ctx || !Number.isFinite(radius) || radius <= 0 || sides < 3) return;
    const baseRotation = Number.isFinite(rotation) ? rotation : -Math.PI / 2;
    for (let i = 0; i < sides; i += 1) {
      const angle = baseRotation + (i / sides) * Math.PI * 2;
      const px = centerX + Math.cos(angle) * radius;
      const py = centerY + Math.sin(angle) * radius;
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
  }

  function drawHalftoneShape(ctx, shape, centerX, centerY, radius, rotationDeg = 0) {
    if (!ctx || radius <= 0) return;
    const rotation = ((Number(rotationDeg) || 0) * Math.PI) / 180;
    switch (shape) {
      case 'square': {
        const side = radius * 2;
        if (Math.abs(rotation) <= 0.0001) {
          ctx.fillRect(centerX - radius, centerY - radius, side, side);
          return;
        }
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(rotation);
        ctx.fillRect(-radius, -radius, side, side);
        ctx.restore();
        return;
      }
      case 'diamond':
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(rotation);
        ctx.beginPath();
        drawRegularPolygon(ctx, 0, 0, radius, 4, Math.PI / 4);
        ctx.fill();
        ctx.restore();
        return;
      case 'pentagon':
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(rotation);
        ctx.beginPath();
        drawRegularPolygon(ctx, 0, 0, radius, 5, -Math.PI / 2);
        ctx.fill();
        ctx.restore();
        return;
      case 'hexagon':
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(rotation);
        ctx.beginPath();
        drawRegularPolygon(ctx, 0, 0, radius, 6, -Math.PI / 2);
        ctx.fill();
        ctx.restore();
        return;
      case 'circle':
      default:
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.fill();
    }
  }

  function shouldApplyInverseDither(gray, x, y, strength, timeSeconds) {
    const amount = clamp(Number(strength ?? 0) || 0, 0, 3);
    if (amount <= 0) return 0;
    const tone = clamp(gray / 255, 0, 1);
    const threshold = bayerThreshold(x, y);
    const drift = (Math.sin((x + 1) * 7.31 + (y + 1) * 3.17 + timeSeconds * 0.75) + 1) * 0.5;
    const pattern = threshold * 0.72 + drift * 0.28;
    const transitioned = clamp((tone - 0.5) * (0.65 + amount * 1.95) + 0.5, 0, 1);
    const edge = transitioned - pattern;
    const softness = 1.1 + amount * 2.2;
    return clamp(edge * softness, 0, 1);
  }

  function invertCssColor(color) {
    const rgbMatch =
      /rgba?\(\s*(\d+(?:\.\d+)?)\s*[, ]\s*(\d+(?:\.\d+)?)\s*[, ]\s*(\d+(?:\.\d+)?)/i.exec(String(color || ''));
    if (rgbMatch) {
      const r = clamp(Math.round(Number(rgbMatch[1]) || 0), 0, 255);
      const g = clamp(Math.round(Number(rgbMatch[2]) || 0), 0, 255);
      const b = clamp(Math.round(Number(rgbMatch[3]) || 0), 0, 255);
      return 'rgb(' + (255 - r) + ', ' + (255 - g) + ', ' + (255 - b) + ')';
    }
    const hexMatch = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(String(color || '').trim());
    if (hexMatch) {
      const hex =
        hexMatch[1].length === 3
          ? hexMatch[1].split('').map((char) => char + char).join('')
          : hexMatch[1];
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      return 'rgb(' + (255 - r) + ', ' + (255 - g) + ', ' + (255 - b) + ')';
    }
    return 'rgb(255, 255, 255)';
  }

  function lerpChannel(from, to, amount) {
    return clamp(Math.round(from + (to - from) * amount), 0, 255);
  }

  function getRetroDuotonePalette() {
    const key = String(SETTINGS.retroDuotone || 'amber-classic');
    return RETRO_DUOTONE_PALETTES[key] || RETRO_DUOTONE_PALETTES['amber-classic'];
  }

  function selectCharset() {
    if (SETTINGS.style === 'letters') {
      const legacySet = String(SETTINGS.letterSet || 'alphabet').toLowerCase();
      return CHARSETS['letters-' + legacySet] || CHARSETS['letters-alphabet'];
    }
    if (SETTINGS.style === 'braille') return BRAILLE_VARIANTS[SETTINGS.brailleVariant] || BRAILLE_VARIANTS.standard;
    if (SETTINGS.style === 'claude') return CHARSETS.blocks;
    if (SETTINGS.style === 'halftone') return HALFTONE_CHARS;
    if (SETTINGS.style === 'retro' || SETTINGS.style === 'winamp') return RETRO_CHARS;
    if (SETTINGS.style === 'terminal') {
      const key = String(SETTINGS.terminalCharset || 'binary');
      return TERMINAL_CHARSET_PRESETS[key] || TERMINAL_CHARSET_PRESETS.binary;
    }
    if (SETTINGS.style === 'classic' && SETTINGS.charset === 'custom') {
      const customSet = typeof SETTINGS.customCharset === 'string'
        ? SETTINGS.customCharset.slice(0, 100)
        : '';
      return customSet.length > 0 ? customSet : CHARSETS.standard;
    }
    if (SETTINGS.style === 'matrix') return MATRIX_CHARS;
    return CHARSETS[SETTINGS.charset] || CHARSETS.standard;
  }

  function getLocalEdgeContrast(values, x, y, cols, rows) {
    const idx = y * cols + x;
    const center = values[idx] ?? 0;
    const left = x > 0 ? values[idx - 1] ?? center : center;
    const right = x + 1 < cols ? values[idx + 1] ?? center : center;
    const up = y > 0 ? values[idx - cols] ?? center : center;
    const down = y + 1 < rows ? values[idx + cols] ?? center : center;
    const gradientX = Math.abs(right - left);
    const gradientY = Math.abs(down - up);
    return clamp((gradientX + gradientY) / 510, 0, 1);
  }

  function getBackgroundDitherColor(r, g, b, gray) {
    if (SETTINGS.style === 'claude') {
      const intensity = clamp(gray + 30, 0, 255);
      return {
        r: clamp(Math.floor(intensity * 1.02), 0, 255),
        g: clamp(Math.floor(intensity * 0.52), 0, 255),
        b: clamp(Math.floor(intensity * 0.1), 0, 255),
      };
    }
    if (SETTINGS.style === 'terminal') {
      const phosphor = clamp(gray + 28, 0, 255);
      return {
        r: clamp(Math.floor(phosphor * 0.14), 0, 96),
        g: phosphor,
        b: clamp(Math.floor(phosphor * 0.24), 0, 116),
      };
    }
    if (SETTINGS.style === 'retro' || SETTINGS.style === 'winamp') {
      const palette = getRetroDuotonePalette();
      const sepia = clamp(Math.floor(gray * 1.04 + 12), 0, 255);
      const tone = clamp(Math.pow(sepia / 255, 0.94), 0, 1);
      return {
        r: lerpChannel(palette.low.r, palette.high.r, tone),
        g: lerpChannel(palette.low.g, palette.high.g, tone),
        b: lerpChannel(palette.low.b, palette.high.b, tone),
      };
    }
    if (SETTINGS.colorMode === 'color') {
      return {
        r: clamp(Math.floor(r), 0, 255),
        g: clamp(Math.floor(g), 0, 255),
        b: clamp(Math.floor(b), 0, 255),
      };
    }
    if (SETTINGS.colorMode === 'green') {
      const intensity = clamp(gray + 20, 0, 255);
      return {
        r: clamp(Math.floor(intensity * 0.2), 0, 255),
        g: intensity,
        b: clamp(Math.floor(intensity * 0.3), 0, 255),
      };
    }
    if (SETTINGS.colorMode === 'amber') {
      const intensity = clamp(gray + 18, 0, 255);
      return {
        r: intensity,
        g: clamp(Math.floor(intensity * 0.72), 0, 255),
        b: clamp(Math.floor(intensity * 0.16), 0, 255),
      };
    }
    if (SETTINGS.colorMode === 'custom') {
      const rawColor = typeof SETTINGS.customColor === 'string' ? SETTINGS.customColor.trim() : '';
      const match = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec(rawColor);
      const hex =
        match && match[1].length === 3
          ? match[1].split('').map((char) => char + char).join('')
          : match
            ? match[1]
            : 'ffffff';
      const baseR = parseInt(hex.slice(0, 2), 16);
      const baseG = parseInt(hex.slice(2, 4), 16);
      const baseB = parseInt(hex.slice(4, 6), 16);
      const intensity = gray / 255;
      return {
        r: clamp(Math.floor(baseR * intensity), 0, 255),
        g: clamp(Math.floor(baseG * intensity), 0, 255),
        b: clamp(Math.floor(baseB * intensity), 0, 255),
      };
    }
    return { r: gray, g: gray, b: gray };
  }

  function getBorderGlowColor() {
    if (SETTINGS.style === 'terminal') return { r: 96, g: 255, b: 164 };
    if (SETTINGS.style === 'claude') return { r: 255, g: 186, b: 118 };
    if (SETTINGS.style === 'retro' || SETTINGS.style === 'winamp') {
      const palette = getRetroDuotonePalette();
      return { ...palette.high };
    }
    if (SETTINGS.colorMode === 'green') return { r: 110, g: 255, b: 175 };
    if (SETTINGS.colorMode === 'amber') return { r: 255, g: 192, b: 118 };
    if (SETTINGS.colorMode === 'custom') {
      const rawColor = typeof SETTINGS.customColor === 'string' ? SETTINGS.customColor.trim() : '';
      const match = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec(rawColor);
      const hex = match ? (match[1].length === 3 ? match[1].split('').map((char) => char + char).join('') : match[1]) : 'ffffff';
      return {
        r: parseInt(hex.slice(0, 2), 16),
        g: parseInt(hex.slice(2, 4), 16),
        b: parseInt(hex.slice(4, 6), 16),
      };
    }
    if (SETTINGS.colorMode === 'color') return { r: 176, g: 214, b: 255 };
    return { r: 255, g: 255, b: 255 };
  }

  function drawBorderGlowOverlay(ctx, width, height, strength) {
    const glowStrength = clamp(Number(strength ?? 0) || 0, 0, 1);
    if (!ctx || width <= 0 || height <= 0 || glowStrength <= 0.001) return;
    const glowColor = getBorderGlowColor();
    const shortestEdge = Math.max(1, Math.min(width, height));
    const glowSize = Math.max(10, shortestEdge * (0.055 + glowStrength * 0.24));
    const edgeAlpha = clamp(0.018 + glowStrength * 0.34, 0, 0.62);
    const cornerRadius = glowSize * 1.35;
    const edgeColor = (alpha) =>
      'rgba(' + glowColor.r + ', ' + glowColor.g + ', ' + glowColor.b + ', ' + clamp(alpha, 0, 1).toFixed(3) + ')';

    ctx.save();
    ctx.globalCompositeOperation = 'screen';
    ctx.globalAlpha = 1;

    const top = ctx.createLinearGradient(0, 0, 0, glowSize);
    top.addColorStop(0, edgeColor(edgeAlpha * 1.12));
    top.addColorStop(0.58, edgeColor(edgeAlpha * 0.44));
    top.addColorStop(1, edgeColor(0));
    ctx.fillStyle = top;
    ctx.fillRect(0, 0, width, glowSize);

    const bottom = ctx.createLinearGradient(0, height, 0, height - glowSize);
    bottom.addColorStop(0, edgeColor(edgeAlpha * 1.12));
    bottom.addColorStop(0.58, edgeColor(edgeAlpha * 0.44));
    bottom.addColorStop(1, edgeColor(0));
    ctx.fillStyle = bottom;
    ctx.fillRect(0, height - glowSize, width, glowSize);

    const left = ctx.createLinearGradient(0, 0, glowSize, 0);
    left.addColorStop(0, edgeColor(edgeAlpha));
    left.addColorStop(0.58, edgeColor(edgeAlpha * 0.4));
    left.addColorStop(1, edgeColor(0));
    ctx.fillStyle = left;
    ctx.fillRect(0, 0, glowSize, height);

    const right = ctx.createLinearGradient(width, 0, width - glowSize, 0);
    right.addColorStop(0, edgeColor(edgeAlpha));
    right.addColorStop(0.58, edgeColor(edgeAlpha * 0.4));
    right.addColorStop(1, edgeColor(0));
    ctx.fillStyle = right;
    ctx.fillRect(width - glowSize, 0, glowSize, height);

    const cornerAlpha = edgeAlpha * 0.9;
    const drawCorner = (x, y) => {
      const radial = ctx.createRadialGradient(x, y, 0, x, y, cornerRadius);
      radial.addColorStop(0, edgeColor(cornerAlpha));
      radial.addColorStop(0.65, edgeColor(cornerAlpha * 0.28));
      radial.addColorStop(1, edgeColor(0));
      ctx.fillStyle = radial;
      ctx.fillRect(x - cornerRadius, y - cornerRadius, cornerRadius * 2, cornerRadius * 2);
    };
    drawCorner(0, 0);
    drawCorner(width, 0);
    drawCorner(0, height);
    drawCorner(width, height);
    ctx.restore();
  }

  function charFromGray(gray, charset, x, y, cols, rows, edgeContrast = 0) {
    const normalized = gray / 255;
    if (SETTINGS.style === 'halftone') {
      const dotRamp = HALFTONE_CHARS;
      const screen =
        (Math.sin((x * 0.82 + y * 0.33) * 1.55) + Math.cos((x * 0.27 - y * 0.94) * 1.25) + 2) * 0.25;
      const adjusted = clamp(Math.pow(normalized, 0.9) * 0.8 + screen * 0.2, 0, 1);
      const idx = Math.floor(adjusted * (dotRamp.length - 1));
      return dotRamp[clamp(idx, 0, dotRamp.length - 1)];
    }
    if (SETTINGS.style === 'braille') {
      const variant = String(SETTINGS.brailleVariant || 'standard');
      const variantBias = variant === 'dense' ? 0.11 : variant === 'sparse' ? -0.08 : 0;
      const screen =
        (Math.sin((x * 0.73 + y * 0.41) * 1.37) + Math.cos((x * 0.29 - y * 0.88) * 1.11) + 2) * 0.25;
      const concentration = clamp(edgeContrast * 1.55 + Math.max(0, normalized - 0.45) * 0.28, 0, 1);
      const adjusted = clamp(
        Math.pow(normalized, 0.88) * 0.82 + screen * 0.11 + concentration * 0.24 + variantBias,
        0,
        1
      );
      const idx = Math.floor(adjusted * (charset.length - 1));
      return charset[clamp(idx, 0, charset.length - 1)];
    }
    if (SETTINGS.style === 'dotcross') {
      const dotRamp = '  .·:oO';
      const crossRamp = '  ·+xX#';
      const screen =
        (Math.sin((x * 0.82 + y * 0.33) * 1.55) + Math.cos((x * 0.27 - y * 0.94) * 1.25) + 2) * 0.25;
      const adjusted = clamp(Math.pow(normalized, 0.9) * 0.82 + screen * 0.18, 0, 1);
      const dotIdx = Math.floor(adjusted * (dotRamp.length - 1));
      const crossIdx = Math.floor(adjusted * (crossRamp.length - 1));
      const edgeMix = clamp(edgeContrast * 1.4 + Math.max(0, adjusted - 0.5) * 0.22, 0, 1);
      const weave =
        (Math.sin((x + 1) * 1.71 + (y + 1) * 2.37) + Math.cos((x + 1) * 0.83 - (y + 1) * 1.29) + 2) * 0.25;
      const useCross = edgeMix > clamp(0.46 + weave * 0.28, 0, 1);
      const glyph = useCross
        ? crossRamp[clamp(crossIdx, 0, crossRamp.length - 1)]
        : dotRamp[clamp(dotIdx, 0, dotRamp.length - 1)];
      return glyph || ' ';
    }
    if (SETTINGS.style === 'particles') {
      const density = clamp(SETTINGS.particleDensity ?? 0.5, 0.05, 1);
      const nx = cols > 1 ? (x / (cols - 1)) * 2 - 1 : 0;
      const ny = rows > 1 ? (y / (rows - 1)) * 2 - 1 : 0;
      const center = 1 - clamp(Math.sqrt(nx * nx + ny * ny), 0, 1);
      const centerBias = Math.pow(center, 1.35) * density * 0.42;
      const edgeBoost = clamp(edgeContrast * 1.6 + Math.max(0, normalized - 0.45) * 0.24, 0, 1);
      const grain = (Math.sin((x + 1) * 12.9898 + (y + 1) * 78.233) + 1) * 0.5;
      const jitter = (grain - 0.5) * (0.18 - density * 0.08);
      const brightnessBias = clamp((SETTINGS.brightness ?? 0) / 50, -1, 1) * 0.12;
      const threshold = clamp(
        1 - density - centerBias * 0.95 - edgeBoost * 0.42 + jitter * 0.9 - brightnessBias * 0.25,
        0.01,
        0.95
      );
      const fillBias = Math.pow(normalized, 0.82) * 0.18 + edgeBoost * 0.15 + Math.max(0, brightnessBias) * 0.1;
      return normalized + fillBias >= threshold ? (SETTINGS.particleChar || '*') : ' ';
    }
    let adjusted = normalized;
    if (SETTINGS.style === 'retro' || SETTINGS.style === 'winamp') {
      const retroNoise = clamp(Number(SETTINGS.retroNoise ?? 0.45) || 0, 0, 1);
      const grain = (Math.sin((x + 1) * 12.9898 + (y + 1) * 78.233) + 1) * 0.5;
      const jitter = (grain - 0.5) * retroNoise * 0.22;
      adjusted = clamp(Math.pow(normalized, 0.78) + jitter, 0, 1);
      const bands = 10 + Math.round(retroNoise * 16);
      adjusted = Math.round(adjusted * bands) / Math.max(1, bands);
    }
    if (SETTINGS.style === 'terminal') adjusted = Math.pow(normalized, 0.82);
    if (SETTINGS.style === 'matrix') adjusted = Math.pow(normalized, 0.7);
    const idx = Math.floor(adjusted * (charset.length - 1));
    return charset[clamp(idx, 0, charset.length - 1)];
  }

  function colorFromMode(r, g, b, gray, x, y, cols, rows, edgeContrast = 0) {
    let particleBoost = 0;
    let particleColorGain = 1;
    if (SETTINGS.style === 'particles') {
      const density = clamp(SETTINGS.particleDensity ?? 0.5, 0.05, 1);
      const nx = cols > 1 ? (x / (cols - 1)) * 2 - 1 : 0;
      const ny = rows > 1 ? (y / (rows - 1)) * 2 - 1 : 0;
      const center = 1 - clamp(Math.sqrt(nx * nx + ny * ny), 0, 1);
      const centerGlow = Math.pow(center, 1.4) * density;
      const edgeGlow = clamp(edgeContrast, 0, 1);
      particleBoost = centerGlow * (24 + density * 72) + edgeGlow * (18 + density * 34);
      particleColorGain = 1 + centerGlow * 0.45 + edgeGlow * 0.22;
    }
    const boostedGray = clamp(gray + particleBoost, 0, 255);

    if (SETTINGS.style === 'claude') {
      const intensity = clamp(gray + 36, 0, 255);
      const red = clamp(Math.floor(intensity * 1.03), 0, 255);
      const green = clamp(Math.floor(intensity * 0.5), 0, 255);
      const blue = clamp(Math.floor(intensity * 0.08), 0, 255);
      return 'rgb(' + red + ', ' + green + ', ' + blue + ')';
    }

    if (SETTINGS.style === 'retro' || SETTINGS.style === 'winamp') {
      const retroNoise = clamp(Number(SETTINGS.retroNoise ?? 0.45) || 0, 0, 1);
      const palette = getRetroDuotonePalette();
      const nx = cols > 1 ? (x / (cols - 1)) * 2 - 1 : 0;
      const ny = rows > 1 ? (y / (rows - 1)) * 2 - 1 : 0;
      const vignette = 1 - clamp(Math.sqrt(nx * nx + ny * ny), 0, 1) * 0.32;
      const grain = Math.sin((x + 1) * 12.9898 + (y + 1) * 78.233);
      const shimmer = Math.sin(x * 0.13 + y * 0.07) * 5;
      const noise = Math.sin((x + 1) * 41.13 + (y + 1) * 17.37 + gray * 0.031);
      const warm = clamp(
        gray * 1.06 + 14 + shimmer + grain * (3 + retroNoise * 7.5) + noise * (1 + retroNoise * 16),
        0,
        255
      );
      const tone = clamp(Math.pow((warm * vignette) / 255, 0.86), 0, 1);
      const red = lerpChannel(palette.low.r, palette.high.r, tone);
      const green = lerpChannel(palette.low.g, palette.high.g, tone);
      const blue = lerpChannel(palette.low.b, palette.high.b, tone);
      return 'rgb(' + red + ', ' + green + ', ' + blue + ')';
    }

    if (SETTINGS.style === 'terminal') {
      const phosphor = clamp(gray + 32, 0, 255);
      const scanShade = ((x + y) & 1) === 0 ? 1 : 0.84;
      const green = clamp(Math.floor(phosphor * scanShade), 0, 255);
      const red = clamp(Math.floor(green * 0.12), 0, 72);
      const blue = clamp(Math.floor(green * 0.2), 0, 88);
      return 'rgb(' + red + ', ' + green + ', ' + blue + ')';
    }

    if (SETTINGS.colorMode === 'color') {
      const boostedR = clamp(Math.floor(r * particleColorGain + particleBoost * 0.22), 0, 255);
      const boostedG = clamp(Math.floor(g * particleColorGain + particleBoost * 0.28), 0, 255);
      const boostedB = clamp(Math.floor(b * particleColorGain + particleBoost * 0.2), 0, 255);
      return 'rgb(' + boostedR + ', ' + boostedG + ', ' + boostedB + ')';
    }

    if (SETTINGS.colorMode === 'green') {
      const intensity = clamp(boostedGray + 25, 0, 255);
      return 'rgb(' + Math.floor(intensity * 0.2) + ', ' + intensity + ', ' + Math.floor(intensity * 0.3) + ')';
    }

    if (SETTINGS.colorMode === 'amber') {
      const intensity = clamp(boostedGray + 20, 0, 255);
      return 'rgb(' + intensity + ', ' + Math.floor(intensity * 0.7) + ', ' + Math.floor(intensity * 0.15) + ')';
    }

    if (SETTINGS.colorMode === 'custom') {
      const rawColor = typeof SETTINGS.customColor === 'string' ? SETTINGS.customColor.trim() : '';
      const match = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.exec(rawColor);
      const hex = match ? (match[1].length === 3 ? match[1].split('').map((char) => char + char).join('') : match[1]) : 'ffffff';
      const baseR = parseInt(hex.slice(0, 2), 16);
      const baseG = parseInt(hex.slice(2, 4), 16);
      const baseB = parseInt(hex.slice(4, 6), 16);
      const intensity = boostedGray / 255;
      const red = clamp(Math.floor(baseR * intensity), 0, 255);
      const green = clamp(Math.floor(baseG * intensity), 0, 255);
      const blue = clamp(Math.floor(baseB * intensity), 0, 255);
      return 'rgb(' + red + ', ' + green + ', ' + blue + ')';
    }

    return 'rgb(' + boostedGray + ', ' + boostedGray + ', ' + boostedGray + ')';
  }

  function applyOverlayFx(gray, x, y, cols, rows, timeSeconds) {
    const preset = SETTINGS.overlayPreset || 'none';
    const strength = clamp(SETTINGS.overlayStrength ?? 0.4, 0, 1);
    if (preset === 'none' || strength <= 0) return gray;

    if (preset === 'noise') {
      const scale = clamp(SETTINGS.noiseScale ?? 24, 4, 120);
      const speed = clamp(SETTINGS.noiseSpeed ?? 1, 0, 4);
      const projection = getDirectionProjection(SETTINGS.noiseDirection || 'right');
      const { primaryNorm, secondaryNorm } = projectDirection(x, y, cols, rows, projection);
      const flowSpan = Math.max(cols, rows);
      const phase = timeSeconds * speed * 2.4;
      const axisPrimary = (primaryNorm * flowSpan + 17.3) / scale;
      const axisSecondary = (secondaryNorm * flowSpan - 9.7) / scale;
      const coherent = Math.sin(axisPrimary + phase) * Math.cos(axisSecondary - phase * 0.73);
      const grain = Math.sin(primaryNorm * flowSpan * 1.37 + secondaryNorm * flowSpan * 2.11 + phase * 6.2);
      const amount = 16 + strength * 72;
      return clamp(gray + (coherent * 0.65 + grain * 0.35) * amount, 0, 255);
    }

    if (preset === 'intervals' || preset === 'lines') {
      const spacing = clamp(SETTINGS.intervalSpacing ?? 12, 4, 64);
      const speed = clamp(SETTINGS.intervalSpeed ?? 1, 0, 4);
      const width = clamp(SETTINGS.intervalWidth ?? 2, 1, 8);
      const projection = getDirectionProjection(SETTINGS.intervalDirection || 'down');
      const { primaryNorm, secondaryNorm } = projectDirection(x, y, cols, rows, projection);
      const flowSpan = Math.max(cols, rows);
      const axisCoord = primaryNorm * flowSpan;
      const crossCoord = secondaryNorm * flowSpan;
      const offsetRaw = timeSeconds * speed * spacing * 1.7;
      const offset = ((offsetRaw % spacing) + spacing) % spacing;
      const phase = (axisCoord + offset) % spacing;
      const distance = Math.min(phase, spacing - phase);
      const lineMask = 1 - clamp(distance / width, 0, 1);
      const wave =
        Math.sin((axisCoord / spacing) * Math.PI * 2 + timeSeconds * speed * 1.8 + (crossCoord / Math.max(flowSpan, 1)) * 1.1);
      const amount = strength * 88;
      return clamp(gray + lineMask * amount * 0.85 + wave * amount * 0.32, 0, 255);
    }

    if (preset === 'beam') {
      const speed = 0.45 + strength * 2.2;
      const width = 0.08 + strength * 0.22;
      const projection = getDirectionProjection(SETTINGS.beamDirection || 'right');
      const { primaryNorm } = projectDirection(x, y, cols, rows, projection);
      const sweepRaw = (timeSeconds * speed) % 1.2;
      const center = ((sweepRaw + 1.2) % 1.2) - 0.1;
      const distance = Math.abs(primaryNorm - center);
      const beam = Math.max(0, 1 - distance / width);
      return clamp(gray + beam * (34 + strength * 120), 0, 255);
    }

    if (preset === 'glitch') {
      const projection = getDirectionProjection(SETTINGS.glitchDirection || 'right');
      const { primaryNorm, secondaryNorm } = projectDirection(x, y, cols, rows, projection);
      const flowSpan = Math.max(cols, rows);
      const secondaryCoord = secondaryNorm * flowSpan;
      const laneHeight = 2 + Math.floor((1 - strength) * 3);
      const lane = Math.floor(secondaryCoord / laneHeight);
      const windowTick = Math.floor(timeSeconds * (0.75 + strength * 1.35));
      const laneChance = (Math.sin((lane + 1) * 19.73 + windowTick * 7.11) + 1) * 0.5;
      const laneActive = laneChance > 0.74 ? 1 : 0;
      const laneSpeed =
        0.12 + ((Math.sin((lane + 1) * 6.37) + 1) * 0.5) * (0.22 + strength * 0.34);
      const lanePhase = (Math.sin((lane + 1) * 2.91) + 1) * 0.5;
      const head = (timeSeconds * laneSpeed + lanePhase) % 1;
      const trailLength = 0.12 + strength * 0.28;
      const distanceAcross = (primaryNorm - head + 1) % 1;
      const trail = Math.max(0, 1 - distanceAcross / trailLength);
      const scanPulse = Math.max(
        0,
        Math.sin(distanceAcross * Math.PI * (5 + strength * 8) - timeSeconds * (2 + strength * 5))
      );
      const rowGlow = laneActive * (trail * (18 + strength * 86) + scanPulse * (6 + strength * 26));
      const syncTear =
        laneActive *
        Math.sin(primaryNorm * Math.PI * 2 * (2 + strength * 4) - timeSeconds * (1.4 + strength * 2.2)) *
        (3 + strength * 14);
      const staticNoise = Math.sin((x + 1) * 17.7 + (y + 1) * 29.3 + timeSeconds * 9.1) * (1.5 + strength * 4.5);
      return clamp(gray + rowGlow + syncTear + staticNoise + secondaryNorm * 0.5, 0, 255);
    }

    if (preset === 'crt') {
      const projection = getDirectionProjection(SETTINGS.crtDirection || 'down');
      const { primaryNorm, secondaryNorm } = projectDirection(x, y, cols, rows, projection);
      const flowSpan = Math.max(cols, rows);
      const primaryCoord = primaryNorm * flowSpan;
      const secondaryCoord = secondaryNorm * flowSpan;
      const nx = (x / Math.max(cols - 1, 1)) * 2 - 1;
      const ny = (y / Math.max(rows - 1, 1)) * 2 - 1;
      const radial = nx * nx * 0.84 + ny * ny * 1.12;
      const curvature = 1 - clamp(radial, 0, 1);
      const edgeFalloff = (1 - curvature) * (24 + strength * 116);
      const scanline = Math.sin((primaryCoord + timeSeconds * (34 + strength * 24)) * Math.PI);
      const triad = Math.sin((secondaryCoord + timeSeconds * 8.5) * 2.9);
      const flicker = Math.sin(timeSeconds * 61) * 0.55 + Math.sin(timeSeconds * 23) * 0.45;
      const rollRaw = (timeSeconds * (0.12 + strength * 0.24)) % 1;
      const rollCenter = (rollRaw + 1) % 1;
      const rollDistance = Math.abs(primaryNorm - rollCenter);
      const rollGlow = Math.max(0, 1 - rollDistance / (0.045 + strength * 0.08));
      const laneToken = Math.sin((secondaryCoord + 1) * 14.37 + Math.floor(timeSeconds * 12) * 1.91);
      const laneActive = laneToken > 0.72 ? 1 : 0;
      const streakRaw = (timeSeconds * (0.55 + strength * 1.35) + secondaryCoord * 0.037) % 1;
      const streakHead = (streakRaw + 1) % 1;
      const streakDistance = Math.abs(primaryNorm - streakHead);
      const streakCore = Math.max(0, 1 - streakDistance / (0.014 + strength * 0.03));
      const streakTicks = Math.max(
        0,
        Math.sin(primaryNorm * 170 - timeSeconds * (28 + strength * 58) + secondaryCoord * 2.4)
      );
      const glitchStreak = laneActive * (streakCore * (8 + strength * 34) + streakTicks * (2 + strength * 10));
      const overdrive = Math.pow(gray / 255, 1.35) * (22 + strength * 72);
      const crush = Math.pow(1 - gray / 255, 1.2) * (8 + strength * 24);
      const boost =
        scanline * (14 + strength * 36) +
        triad * (6 + strength * 14) +
        flicker * (5 + strength * 14) +
        rollGlow * (18 + strength * 64) +
        glitchStreak +
        overdrive -
        crush;
      return clamp(gray + boost - edgeFalloff, 0, 255);
    }

    return gray;
  }

  function drawError(message) {
    ctx.clearRect(0, 0, renderWidth, renderHeight);
    ctx.fillStyle = '#fca5a5';
    ctx.font = '16px ' + (SETTINGS.renderFont || 'Helvetica, Arial, sans-serif');
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(message, renderWidth / 2, renderHeight / 2);
  }

  function readBounds() {
    const rect = mount.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width || mount.clientWidth || window.innerWidth || 1));
    const height = Math.max(1, Math.round(rect.height || mount.clientHeight || window.innerHeight || 1));
    return {
      left: rect.left,
      top: rect.top,
      width,
      height,
      right: rect.left + width,
      bottom: rect.top + height
    };
  }

  function resize() {
    bounds = readBounds();
    viewWidth = bounds.width;
    viewHeight = bounds.height;
  }

  function parseAspectRatio(aspectValue) {
    if (!aspectValue || aspectValue === 'source') return null;
    const parts = String(aspectValue).split(':');
    if (parts.length !== 2) return null;
    const w = Number(parts[0]);
    const h = Number(parts[1]);
    if (!Number.isFinite(w) || !Number.isFinite(h) || w <= 0 || h <= 0) return null;
    return w / h;
  }

  function getSourceSize(element) {
    return {
      width: element.videoWidth || element.naturalWidth || 0,
      height: element.videoHeight || element.naturalHeight || 0
    };
  }

  function getCoverCropRect(sourceWidth, sourceHeight, targetAspect) {
    const safeSourceWidth = Math.max(1, Number(sourceWidth) || 1);
    const safeSourceHeight = Math.max(1, Number(sourceHeight) || 1);
    const safeTargetAspect = Math.max(0.0001, Number(targetAspect) || safeSourceWidth / safeSourceHeight);
    const sourceAspect = safeSourceWidth / safeSourceHeight;
    let cropX = 0;
    let cropY = 0;
    let cropWidth = safeSourceWidth;
    let cropHeight = safeSourceHeight;

    if (sourceAspect > safeTargetAspect) {
      cropWidth = safeSourceHeight * safeTargetAspect;
      cropX = (safeSourceWidth - cropWidth) * 0.5;
    } else if (sourceAspect < safeTargetAspect) {
      cropHeight = safeSourceWidth / safeTargetAspect;
      cropY = (safeSourceHeight - cropHeight) * 0.5;
    }

    return { cropX, cropY, cropWidth, cropHeight };
  }

  function proceduralField(x, y, cols, rows, timeSeconds) {
    const nx = cols > 1 ? (x / (cols - 1)) * 2 - 1 : 0;
    const ny = rows > 1 ? (y / (rows - 1)) * 2 - 1 : 0;
    const scale = clamp(SOURCE.proceduralScale ?? 1, 0.45, 2.4);
    const speed = clamp(SOURCE.proceduralSpeed ?? 1, 0.2, 3.5);
    const t = timeSeconds * speed;
    const radius = Math.sqrt(nx * nx + ny * ny);
    const angle = Math.atan2(ny, nx);
    const flow = Math.sin((nx * 3.6 + t * 1.2) * scale);
    const drift = Math.cos((ny * 4.8 - t * 0.9) * scale);
    const ring = Math.sin((radius * 13.5 - t * 2.35 + angle * 2.6) * scale);
    const grain = Math.sin((nx * 18.7 + ny * 11.3 + t * 4.7) * scale);
    return clamp((flow * 0.33 + drift * 0.26 + ring * 0.31 + grain * 0.1 + 1) * 0.5, 0, 1);
  }

  function isActiveForRendering() {
    const requiresInView = EXPORT_OPTIONS.pauseWhenOffscreen !== false;
    return isPageVisible && (!requiresInView || isInViewport);
  }

  function isPlayableVideoSource(value) {
    return Boolean(value && typeof value.play === 'function' && typeof value.pause === 'function');
  }

  function syncSourcePlayback(shouldRun) {
    if (!source || source.kind === 'procedural' || SOURCE.type === 'image') return;
    if (!isPlayableVideoSource(source)) return;
    if (SOURCE.type === 'camera' && stream) {
      const tracks = typeof stream.getVideoTracks === 'function' ? stream.getVideoTracks() : stream.getTracks();
      tracks.forEach((track) => {
        track.enabled = shouldRun;
      });
    }
    if (shouldRun) {
      source.play().catch(() => {});
      return;
    }
    source.pause();
  }

  function requiresContinuousRendering(interactionEnabled = Boolean(EXPORT_OPTIONS.enableInteractionEffects)) {
    return SOURCE.type !== 'image' || SETTINGS.overlayPreset !== 'none' || (interactionEnabled && (pointer.inside || clickBursts.length > 0));
  }

  function getTargetFps(interactionEnabled) {
    const maxFps = clamp(Number(EXPORT_OPTIONS.maxFps ?? 30) || 30, 6, 60);
    if (EXPORT_OPTIONS.adaptivePerformance === false) return maxFps;
    const idleFps = clamp(Number(EXPORT_OPTIONS.idleFps ?? 12) || 12, 1, maxFps);
    const isInteractive = interactionEnabled && (pointer.inside || clickBursts.length > 0);
    return isInteractive ? maxFps : idleFps;
  }

  function handleRenderActivityChange(forceNextFrame = false) {
    if (!isActiveForRendering()) {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      pendingForceRender = false;
      pointer = { ...pointer, inside: false };
      if (clickBursts.length) clickBursts = [];
      syncSourcePlayback(false);
      reportFps(0);
      return;
    }

    syncSourcePlayback(true);
    if (forceNextFrame) {
      scheduleRender(true);
      return;
    }
    if (requiresContinuousRendering()) {
      scheduleRender();
    }
  }

  function handleDocumentVisibilityChange() {
    const nextVisible = document.visibilityState !== 'hidden';
    if (nextVisible === isPageVisible) return;
    isPageVisible = nextVisible;
    handleRenderActivityChange(nextVisible);
  }

  function handleIntersection(entries) {
    const entry = entries && entries[0];
    if (!entry) return;
    const nextInViewport = entry.isIntersecting && entry.intersectionRatio > 0;
    if (nextInViewport === isInViewport) return;
    isInViewport = nextInViewport;
    handleRenderActivityChange(nextInViewport);
  }

  function handleWindowResize() {
    resize();
    scheduleRender(true);
  }

  function scheduleRender(force = false) {
    if (force) pendingForceRender = true;
    if (!isActiveForRendering()) {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      return;
    }
    if (!rafId) rafId = requestAnimationFrame(renderFrame);
  }

  function toCanvasPoint(event) {
    const rect = canvas.getBoundingClientRect();
    const inside =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;
    if (!inside) return null;
    const x = ((event.clientX - rect.left) / Math.max(rect.width, 1)) * renderWidth;
    const y = ((event.clientY - rect.top) / Math.max(rect.height, 1)) * renderHeight;
    return { x: clamp(x, 0, renderWidth), y: clamp(y, 0, renderHeight) };
  }

  function handleWindowPointerMove(event) {
    const point = toCanvasPoint(event);
    if (!point) {
      if (pointer.inside) {
        pointer = { ...pointer, inside: false };
        scheduleRender();
      }
      return;
    }
    pointer = { inside: true, x: point.x, y: point.y };
    scheduleRender();
  }

  function handleWindowPointerDown(event) {
    const point = toCanvasPoint(event);
    if (!point) return;
    pointer = { inside: true, x: point.x, y: point.y };
    clickBursts = [
      ...clickBursts.slice(-2),
      { x: point.x, y: point.y, startedAt: performance.now(), seed: Math.random() * Math.PI * 2 }
    ];
    scheduleRender();
  }

  function handleWindowBlur() {
    if (!pointer.inside) return;
    pointer = { ...pointer, inside: false };
    scheduleRender();
  }

  async function loadSource() {
    if (SOURCE.type === 'procedural') {
      return { kind: 'procedural' };
    }

    if (SOURCE.type === 'camera') {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
      const video = document.createElement('video');
      video.srcObject = stream;
      video.muted = true;
      video.playsInline = true;
      await video.play();
      return video;
    }

    if (SOURCE.type === 'video') {
      const video = document.createElement('video');
      video.src = SOURCE.url;
      video.preload = 'auto';
      video.crossOrigin = 'anonymous';
      video.muted = true;
      video.loop = true;
      video.playsInline = true;
      sourceLoopHandler = () => {
        try {
          video.currentTime = 0.001;
          const resumePromise = video.play();
          if (resumePromise && typeof resumePromise.catch === 'function') {
            resumePromise.catch(() => {});
          }
          scheduleRender(true);
        } catch {
          // Ignore loop recovery errors to keep render alive.
        }
      };
      video.addEventListener('ended', sourceLoopHandler);
      await new Promise((resolve, reject) => {
        video.onloadeddata = resolve;
        video.onerror = reject;
      });
      video.currentTime = 0;
      await video.play();
      return video;
    }

    const image = new Image();
    image.crossOrigin = 'anonymous';
    image.src = SOURCE.url;
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = reject;
    });
    return image;
  }

  function renderFrame(now) {
    rafId = null;
    if (!source) return;
    if (!isActiveForRendering()) {
      syncSourcePlayback(false);
      return;
    }
    const interactionEnabled = Boolean(EXPORT_OPTIONS.enableInteractionEffects);
    if (interactionEnabled) {
      clickBursts = clickBursts.filter((burst) => now - burst.startedAt < CLICK_BURST_DURATION_MS);
    } else if (clickBursts.length) {
      clickBursts = [];
    }
    const forceRender = pendingForceRender;
    pendingForceRender = false;
    const targetFps = getTargetFps(interactionEnabled);
    const minFrameInterval = 1000 / Math.max(1, targetFps);
    if (!forceRender && lastRenderTime > 0 && now - lastRenderTime < minFrameInterval) {
      scheduleRender();
      return;
    }
    lastRenderTime = now;
    const frameStartedAt = performance.now();
    fpsFrameCount += 1;
    if (!fpsWindowStart) fpsWindowStart = now;
    const proceduralMode = source.kind === 'procedural';

    const fontSize = clamp(SETTINGS.fontSize || 10, 6, 24);
    const spacing = clamp(SETTINGS.charSpacing ?? 1, 0.7, 2);
    const renderFont = SETTINGS.renderFont || 'Helvetica, Arial, sans-serif';
    const fontDeclaration = fontSize + 'px ' + renderFont;
    ctx.font = fontDeclaration;
    const measuredCharWidth = ctx.measureText('M').width;
    const charWidth = Math.max(fontSize * 0.45, measuredCharWidth || fontSize * 0.62);
    const cellWidth = charWidth * spacing;
    const cellHeight = fontSize * spacing;
    const cols = Math.max(24, Math.floor(viewWidth / cellWidth));
    let contentAspect = viewWidth / Math.max(viewHeight, 1);
    const requestedAspect = parseAspectRatio(SETTINGS.outputAspect);
    let sourceSize = null;

    if (!proceduralMode) {
      sourceSize = getSourceSize(source);
      if (!sourceSize.width || !sourceSize.height) {
        scheduleRender();
        return;
      }
      contentAspect = requestedAspect || sourceSize.width / sourceSize.height;

      if (SOURCE.type === 'video' && isPlayableVideoSource(source)) {
        const sourceDuration = Number(source.duration);
        if (Number.isFinite(sourceDuration) && sourceDuration > 0) {
          const sourceFps = clamp(Number(SOURCE.fps) || 6, 1, 24);
          const loopThreshold = clamp(Math.max(0.24, 2 / sourceFps), 0.12, 0.75);
          if (sourceDuration - source.currentTime <= loopThreshold) {
            try {
              source.currentTime = 0.001;
              if (source.paused) {
                source.play().catch(() => {});
              }
              scheduleRender(true);
            } catch {
              // Ignore near-end seek errors and keep rendering.
            }
          }
        }
      }
    }

    const cellAspectRatio = cellWidth / Math.max(cellHeight, 1);
    const rows = Math.max(12, Math.round((1 / Math.max(contentAspect, 0.0001)) * cols * cellAspectRatio));
    const outputWidth = Math.max(1, Math.floor(cols * cellWidth));
    const outputHeight = Math.max(1, Math.ceil(rows * cellHeight + cellHeight));
    const dpr = window.devicePixelRatio || 1;
    if (
      outputWidth !== renderWidth ||
      outputHeight !== renderHeight ||
      canvas.width !== Math.max(1, Math.round(outputWidth * dpr)) ||
      canvas.height !== Math.max(1, Math.round(outputHeight * dpr))
    ) {
      renderWidth = outputWidth;
      renderHeight = outputHeight;
      canvas.width = Math.max(1, Math.round(renderWidth * dpr));
      canvas.height = Math.max(1, Math.round(renderHeight * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.font = fontDeclaration;
    }
    lastCharCount = cols * rows;

    const charset = selectCharset();
    const timeSeconds = now * 0.001;
    const grayscale = new Float32Array(cols * rows);
    let data;

    sampleCanvas.width = cols;
    sampleCanvas.height = rows;

    if (proceduralMode) {
      const proceduralPreset = SOURCE.proceduralPreset || 'flow';
      const proceduralPixels = new Uint8ClampedArray(cols * rows * 4);
      data = proceduralPixels;

      for (let y = 0; y < rows; y += 1) {
        for (let x = 0; x < cols; x += 1) {
          const idx = y * cols + x;
          const offset = idx * 4;
          const field = proceduralField(x, y, cols, rows, timeSeconds);
          const pulse = 0.5 + 0.5 * Math.sin(timeSeconds * 1.8 + x * 0.06 - y * 0.04);
          const mixed = clamp(field * 0.78 + pulse * 0.22, 0, 1);
          const baseGray = Math.floor(mixed * 255);

          let r = baseGray;
          let g = baseGray;
          let b = baseGray;

          if (proceduralPreset === 'plasma') {
            r = clamp(Math.floor(baseGray * 0.72 + 92 * (0.5 + 0.5 * Math.sin(timeSeconds * 1.1 + y * 0.09))), 0, 255);
            g = clamp(Math.floor(baseGray * 0.48 + 74 * (0.5 + 0.5 * Math.cos(timeSeconds * 1.6 + x * 0.07))), 0, 255);
            b = clamp(Math.floor(baseGray * 0.84 + 102 * (0.5 + 0.5 * Math.sin(timeSeconds * 1.35 + (x + y) * 0.05))), 0, 255);
          } else if (proceduralPreset === 'mono') {
            const mono = clamp(Math.floor(baseGray * 1.08), 0, 255);
            r = mono;
            g = mono;
            b = mono;
          } else {
            r = clamp(Math.floor(baseGray * 0.64 + 86 * (0.5 + 0.5 * Math.sin(timeSeconds * 1.2 + x * 0.11))), 0, 255);
            g = clamp(Math.floor(baseGray * 0.82 + 64 * (0.5 + 0.5 * Math.sin(timeSeconds * 1.45 + y * 0.08))), 0, 255);
            b = clamp(Math.floor(baseGray * 0.58 + 74 * (0.5 + 0.5 * Math.cos(timeSeconds * 1.05 + (x - y) * 0.07))), 0, 255);
          }

          proceduralPixels[offset] = r;
          proceduralPixels[offset + 1] = g;
          proceduralPixels[offset + 2] = b;
          proceduralPixels[offset + 3] = 255;

          const toned = applyTone(baseGray);
          grayscale[idx] = applyOverlayFx(toned, x, y, cols, rows, timeSeconds);
        }
      }
    } else {
      const sampleTargetAspect = (cols * cellWidth) / Math.max(rows * cellHeight, 1);
      const { cropX, cropY, cropWidth, cropHeight } = getCoverCropRect(
        sourceSize.width,
        sourceSize.height,
        sampleTargetAspect
      );
      sampleCtx.drawImage(source, cropX, cropY, cropWidth, cropHeight, 0, 0, cols, rows);
      const pixels = sampleCtx.getImageData(0, 0, cols, rows);
      data = pixels.data;

      for (let y = 0; y < rows; y += 1) {
        for (let x = 0; x < cols; x += 1) {
          const idx = y * cols + x;
          const offset = idx * 4;
          const r = data[offset];
          const g = data[offset + 1];
          const b = data[offset + 2];
          const baseGray = 0.299 * r + 0.587 * g + 0.114 * b;
          const toned = applyTone(baseGray);
          grayscale[idx] = applyOverlayFx(toned, x, y, cols, rows, timeSeconds);
        }
      }
    }

    if (SETTINGS.ditherType === 'bayer') {
      for (let y = 0; y < rows; y += 1) {
        for (let x = 0; x < cols; x += 1) {
          const idx = y * cols + x;
          const threshold = bayerThreshold(x, y);
          const offset = (threshold - 0.5) * 255 * SETTINGS.ditherStrength;
          grayscale[idx] = clamp(grayscale[idx] + offset, 0, 255);
        }
      }
    }

    if (SETTINGS.ditherType === 'floyd-steinberg' || SETTINGS.ditherType === 'atkinson') {
      const work = new Float32Array(grayscale);
      for (let y = 0; y < rows; y += 1) {
        for (let x = 0; x < cols; x += 1) {
          const idx = y * cols + x;
          const oldValue = work[idx];
          const step = 255 / Math.max(2, charset.length - 1);
          const newValue = Math.round(oldValue / step) * step;
          const error = (oldValue - newValue) * SETTINGS.ditherStrength;
          work[idx] = clamp(newValue, 0, 255);

          if (SETTINGS.ditherType === 'floyd-steinberg') {
            if (x + 1 < cols) work[idx + 1] += (error * 7) / 16;
            if (x - 1 >= 0 && y + 1 < rows) work[idx + cols - 1] += (error * 3) / 16;
            if (y + 1 < rows) work[idx + cols] += (error * 5) / 16;
            if (x + 1 < cols && y + 1 < rows) work[idx + cols + 1] += error / 16;
          } else {
            if (x + 1 < cols) work[idx + 1] += error / 8;
            if (x + 2 < cols) work[idx + 2] += error / 8;
            if (x - 1 >= 0 && y + 1 < rows) work[idx + cols - 1] += error / 8;
            if (y + 1 < rows) work[idx + cols] += error / 8;
            if (x + 1 < cols && y + 1 < rows) work[idx + cols + 1] += error / 8;
            if (y + 2 < rows) work[idx + cols * 2] += error / 8;
          }
        }
      }
      for (let i = 0; i < grayscale.length; i += 1) {
        grayscale[i] = clamp(work[i], 0, 255);
      }
    }

    ctx.clearRect(0, 0, renderWidth, renderHeight);
    ctx.font = fontDeclaration;
    ctx.textBaseline = 'top';
    const hoverAttractStrength = clamp(SETTINGS.hoverStrength ?? 24, 4, 64);
    const hoverAreaSize = clamp(SETTINGS.mouseAreaSize ?? HOVER_ATTRACT_RADIUS, 40, 640);
    const hoverSpread = clamp(SETTINGS.mouseSpread ?? 1, 0.25, 3);
    const hoverDirection = SETTINGS.mouseInteractionMode === 'push' ? -1 : 1;
    const bgDitherStrength = clamp(Number(SETTINGS.bgDither ?? 0) || 0, 0, 3);
    const inverseDitherStrength = clamp(Number(SETTINGS.inverseDither ?? 0) || 0, 0, 3);
    const foregroundOpacity = clamp(Number(SETTINGS.opacity ?? 1) || 0, 0, 1);
    const vignetteStrength = clamp(Number(SETTINGS.vignette ?? 0) || 0, 0, 1);
    const borderGlowStrength = clamp(Number(SETTINGS.borderGlow ?? 0) || 0, 0, 1);
    const invertedBackground = invertCssColor(SETTINGS.backgroundColor || '#000000');
    const hasPointerAttraction = interactionEnabled && pointer.inside;
    const hasBurst = interactionEnabled && clickBursts.length > 0;
    const matrixMode = SETTINGS.overlayPreset === 'matrix';
    const matrixStrength = clamp(SETTINGS.overlayStrength ?? 0.45, 0, 1);
    let matrixBoost = null;

    if (matrixMode) {
      const matrixScale = clamp(SETTINGS.matrixScale ?? 15, 6, 48);
      const matrixSpeed = clamp(SETTINGS.matrixSpeed ?? 0.1, 0.1, 4);
      const laneScale = clamp(matrixScale / 12, 0.6, 4);
      const projection = getDirectionProjection(SETTINGS.matrixDirection || 'down');
      const primaryCount = Math.max(cols, rows);
      const secondaryCount = Math.max(cols, rows);
      const laneCount = Math.max(6, Math.ceil(secondaryCount / laneScale));
      if (
        matrixRainState.laneCount !== laneCount ||
        matrixRainState.primaryCount !== primaryCount ||
        matrixRainState.speeds.length !== laneCount
      ) {
        matrixRainState = {
          laneCount,
          primaryCount,
          speeds: Array.from({ length: laneCount }, () => 0.55 + Math.random() * 1.85),
          phases: Array.from({ length: laneCount }, () => Math.random() * (primaryCount + 36)),
          lengths: Array.from({ length: laneCount }, () =>
            Math.max(7, Math.round(primaryCount * (0.2 + Math.random() * 0.38)))
          ),
        };
      }

      matrixBoost = new Float32Array(cols * rows);
      const laneHeads = new Float32Array(laneCount);
      const laneLengths = new Float32Array(laneCount);
      for (let lane = 0; lane < laneCount; lane += 1) {
        const trailLength = matrixRainState.lengths[lane];
        const cycle = primaryCount + trailLength + 12;
        const head =
          ((timeSeconds * matrixRainState.speeds[lane] * matrixSpeed * primaryCount +
            matrixRainState.phases[lane]) %
            cycle) -
          trailLength;
        laneHeads[lane] = head;
        laneLengths[lane] = trailLength;

        if (Math.random() < 0.0032) {
          matrixRainState.speeds[lane] = 0.55 + Math.random() * 1.85;
          matrixRainState.phases[lane] = Math.random() * (primaryCount + 36);
          matrixRainState.lengths[lane] = Math.max(7, Math.round(primaryCount * (0.2 + Math.random() * 0.38)));
        }
      }

      for (let y = 0; y < rows; y += 1) {
        for (let x = 0; x < cols; x += 1) {
          const idx = y * cols + x;
          const { primaryNorm, secondaryNorm } = projectDirection(x, y, cols, rows, projection);
          const lane = clamp(Math.floor(secondaryNorm * laneCount), 0, laneCount - 1);
          const primary = primaryNorm * (primaryCount - 1);
          const distance = laneHeads[lane] - primary;
          if (distance < 0 || distance > laneLengths[lane]) continue;
          const falloff = 1 - distance / (laneLengths[lane] + 1);
          matrixBoost[idx] = falloff * (44 + matrixStrength * 148 + falloff * (62 + matrixStrength * 30));
        }
      }
    }

    ctx.globalAlpha = foregroundOpacity;
    for (let y = 0; y < rows; y += 1) {
      for (let x = 0; x < cols; x += 1) {
        const idx = y * cols + x;
        const pixelOffset = idx * 4;
        const gray = Math.round(grayscale[idx]);
        const inverseCoverage = shouldApplyInverseDither(gray, x, y, inverseDitherStrength, timeSeconds);
        const invertCell = inverseCoverage > 0.12;
        const mappedGray = clamp(Math.round(gray + (255 - gray * 2) * inverseCoverage), 0, 255);
        const r = data[pixelOffset];
        const g = data[pixelOffset + 1];
        const b = data[pixelOffset + 2];
        const nx = cols > 1 ? (x / (cols - 1)) * 2 - 1 : 0;
        const ny = rows > 1 ? (y / (rows - 1)) * 2 - 1 : 0;
        const radial = Math.sqrt(nx * nx + ny * ny) / Math.SQRT2;
        const vignetteCore = Math.pow(clamp(1 - radial, 0, 1), 1 + vignetteStrength * 2);
        const vignetteFactor = 1 - vignetteStrength + vignetteStrength * vignetteCore;
        const cellAlpha = foregroundOpacity * vignetteFactor;
        if (cellAlpha <= 0.002) continue;
        ctx.globalAlpha = cellAlpha;
        const baseX = x * cellWidth;
        const baseY = y * cellHeight;
        if (bgDitherStrength > 0) {
          const tone = gray / 255;
          const threshold = bayerThreshold(x, y);
          const drift = (Math.sin((x + 1) * 7.31 + (y + 1) * 3.17 + timeSeconds * 0.75) + 1) * 0.5;
          const pattern = threshold * 0.72 + drift * 0.28;
          const coverage = clamp(tone * (0.92 + bgDitherStrength * 0.9) - pattern + 0.34, 0, 1);
          if (coverage > 0.04) {
            const dotFactor = clamp(0.18 + coverage * (0.85 + bgDitherStrength * 0.5), 0.12, 1);
            const dotSize = Math.max(0.45, Math.min(cellWidth, cellHeight) * dotFactor);
            const insetX = (cellWidth - dotSize) * 0.5;
            const insetY = (cellHeight - dotSize) * 0.5;
            const tint = getBackgroundDitherColor(r, g, b, gray);
            const alpha = clamp(coverage * (0.05 + bgDitherStrength * 0.34), 0, 1);
            ctx.fillStyle = 'rgba(' + tint.r + ', ' + tint.g + ', ' + tint.b + ', ' + alpha.toFixed(3) + ')';
            ctx.fillRect(baseX + insetX, baseY + insetY, dotSize, dotSize);
          }
        }

        if (inverseCoverage > 0.01) {
          const invAlpha = clamp(inverseCoverage * (0.08 + inverseDitherStrength * 0.34), 0, 1);
          if (invAlpha > 0.005) {
            const previousAlpha = ctx.globalAlpha;
            ctx.globalAlpha = previousAlpha * invAlpha;
            ctx.fillStyle = invertedBackground;
            ctx.fillRect(baseX, baseY, cellWidth, cellHeight);
            ctx.globalAlpha = previousAlpha;
          }
        }

        const baseColor = colorFromMode(r, g, b, mappedGray, x, y, cols, rows);
        ctx.fillStyle = invertCell ? invertCssColor(baseColor) : baseColor;
        let drawX = baseX;
        let drawY = baseY;
        let centerX = drawX + cellWidth * 0.5;
        let centerY = drawY + cellHeight * 0.5;

        if (hasPointerAttraction || hasBurst) {
          let offsetX = 0;
          let offsetY = 0;

          if (hasPointerAttraction) {
            const dx = pointer.x - centerX;
            const dy = pointer.y - centerY;
            const distance = Math.hypot(dx, dy);
            if (distance > 0.0001 && distance < hoverAreaSize) {
              const falloff = 1 - distance / hoverAreaSize;
              const spreadFactor = Math.pow(falloff, 1 / hoverSpread);
              const pull = spreadFactor * spreadFactor * hoverAttractStrength * hoverDirection;
              offsetX += (dx / distance) * pull;
              offsetY += (dy / distance) * pull;
            }
          }

          if (hasBurst) {
            for (let burstIndex = 0; burstIndex < clickBursts.length; burstIndex += 1) {
              const burst = clickBursts[burstIndex];
              const age = now - burst.startedAt;
              if (age >= CLICK_BURST_DURATION_MS) continue;
              const progress = clamp(age / CLICK_BURST_DURATION_MS, 0, 1);
              const dx = centerX - burst.x;
              const dy = centerY - burst.y;
              const distance = Math.hypot(dx, dy);
              if (distance >= CLICK_BURST_RADIUS) continue;
              const falloff = 1 - distance / CLICK_BURST_RADIUS;
              const impulse =
                CLICK_BURST_STRENGTH *
                falloff *
                (1 - progress * 0.55) *
                (1.25 + Math.sin(progress * Math.PI) * 0.45);
              let dirX = 1;
              let dirY = 0;
              if (distance > 0.0001) {
                dirX = dx / distance;
                dirY = dy / distance;
              } else {
                const angle = (idx + burst.seed) * 0.61803398875;
                dirX = Math.cos(angle);
                dirY = Math.sin(angle);
              }
              offsetX += dirX * impulse;
              offsetY += dirY * impulse;
            }
          }

          drawX += offsetX;
          drawY += offsetY;
          centerX += offsetX;
          centerY += offsetY;
        }

        if (matrixMode) {
          const boost = matrixBoost ? matrixBoost[idx] : 0;
          const ambient = 6 + matrixStrength * 14;
          const baseContrast = clamp((mappedGray - 128) * (1.2 + matrixStrength * 0.55) + 128, 0, 255);
          const composedGray = clamp(Math.round(baseContrast * 0.38 + boost * 0.78 + ambient), 0, 255);
          if (composedGray < 20) continue;

          const glyphClock = timeSeconds * (10 + clamp(SETTINGS.matrixSpeed ?? 0.1, 0.1, 4) * 16);
          const drift =
            Math.sin((x + 1) * 2.17 + glyphClock * 1.7) +
            Math.cos((y + 1) * 1.93 - glyphClock * 1.1);
          const scramble = Math.sin((x + 1) * 91.13 + (y + 1) * 37.77 + glyphClock * 5.3 + boost * 0.06);
          const noise = drift * 0.28 + scramble * 0.72;
          let mapped = Math.floor(clamp((noise + 2) / 4, 0, 1) * (MATRIX_CHARS.length - 1));
          const jumpToken = Math.sin((Math.floor(glyphClock * 2.6) + x * 13 + y * 7) * 12.9898);
          if (jumpToken > 0.93) {
            mapped = 1 + ((Math.floor(glyphClock * 11) + x * 3 + y * 5) % (MATRIX_CHARS.length - 1));
          }
          const char = MATRIX_CHARS[clamp(mapped, 1, MATRIX_CHARS.length - 1)];
          if (char === ' ') continue;

          const isHead = boost > 182;
          const glowAlpha = clamp(0.08 + composedGray / 620 + (isHead ? 0.12 : 0), 0, 0.56);
          const glowGreen = clamp(Math.floor(72 + composedGray * 0.58), 0, 255);
          const glowRed = clamp(Math.floor(glowGreen * 0.24), 0, 160);
          const glowBlue = clamp(Math.floor(glowGreen * 0.34), 0, 180);
          const glowColor = 'rgb(' + glowRed + ', ' + glowGreen + ', ' + glowBlue + ')';
          const glowShadowColor = 'rgba(' + glowRed + ', ' + glowGreen + ', ' + glowBlue + ', ' + glowAlpha + ')';
          ctx.fillStyle = invertCell ? invertCssColor(glowColor) : glowColor;
          ctx.shadowColor = invertCell ? invertCssColor(glowShadowColor) : glowShadowColor;
          ctx.shadowBlur = isHead ? Math.max(3, fontSize * 0.75) : Math.max(1.5, fontSize * 0.32);
          ctx.fillText(char, drawX, drawY);
          ctx.shadowBlur = 0;
          continue;
        }

        if (SETTINGS.style === 'halftone') {
          const halftoneShape = String(SETTINGS.halftoneShape || 'circle');
          const halftoneSize = clamp(Number(SETTINGS.halftoneSize ?? 1) || 1, 0.4, 2.2);
          const halftoneRotation = clamp(Number(SETTINGS.halftoneRotation ?? 0) || 0, -180, 180);
          const normalized = mappedGray / 255;
          const screen =
            (Math.sin((x * 0.82 + y * 0.33) * 1.55) + Math.cos((x * 0.27 - y * 0.94) * 1.25) + 2) * 0.25;
          const dotLevel = clamp(Math.pow(normalized, 0.92) * 0.82 + screen * 0.18, 0, 1);
          const maxRadius = Math.max(0.1, Math.min(cellWidth, cellHeight) * 0.5);
          const radius = maxRadius * dotLevel * halftoneSize;
          if (radius < 0.35) continue;

          drawHalftoneShape(ctx, halftoneShape, centerX, centerY, radius, halftoneRotation);
          continue;
        }

        if (SETTINGS.style === 'line') {
          const normalized = mappedGray / 255;
          const lengthScale = clamp(SETTINGS.lineLength ?? 1, 0.1, 2.5);
          const widthScale = clamp(SETTINGS.lineWidth ?? 1, 0.2, 2.5);
          const thicknessSetting = clamp(SETTINGS.lineThickness ?? 1.6, 0.2, 8);
          const rotationDeg = SETTINGS.lineRotation ?? 0;
          const screen =
            (Math.sin((x * 0.79 + y * 0.41) * 1.37) + Math.cos((x * 0.33 - y * 0.93) * 1.09) + 2) * 0.25;
          const angle = (rotationDeg * Math.PI) / 180 + (screen - 0.5) * 0.55;
          const spanBase = Math.max(0.8, Math.min(cellWidth, cellHeight) * widthScale);
          const span = spanBase * clamp(normalized * lengthScale, 0.05, 1.5);
          if (span < 0.6) continue;
          const half = span * 0.5;
          const x0 = centerX - Math.cos(angle) * half;
          const y0 = centerY - Math.sin(angle) * half;
          const x1 = centerX + Math.cos(angle) * half;
          const y1 = centerY + Math.sin(angle) * half;
          const thicknessPx = clamp(thicknessSetting, 0.2, Math.max(0.2, Math.min(cellWidth, cellHeight) * 1.4));
          const lineColor = colorFromMode(r, g, b, mappedGray, x, y, cols, rows);
          ctx.strokeStyle = invertCell ? invertCssColor(lineColor) : lineColor;
          ctx.lineWidth = thicknessPx;
          ctx.lineCap = 'round';
          ctx.beginPath();
          ctx.moveTo(x0, y0);
          ctx.lineTo(x1, y1);
          ctx.stroke();
          continue;
        }

        const edgeContrast =
          SETTINGS.style === 'dotcross' || SETTINGS.style === 'braille' || SETTINGS.style === 'particles'
            ? getLocalEdgeContrast(grayscale, x, y, cols, rows)
            : 0;
        const brailleVariant = String(SETTINGS.brailleVariant || 'standard');
        const brailleBoost =
          SETTINGS.style === 'braille'
            ? 8 + edgeContrast * 40 + (brailleVariant === 'dense' ? 10 : brailleVariant === 'sparse' ? -4 : 4)
            : 0;
        const particleDensity = clamp(SETTINGS.particleDensity ?? 0.5, 0.05, 1);
        const particleBoost =
          SETTINGS.style === 'particles' ? edgeContrast * 44 + (particleDensity - 0.5) * 12 : 0;
        const glyphGray =
          SETTINGS.style === 'braille'
            ? clamp(mappedGray + brailleBoost, 0, 255)
            : SETTINGS.style === 'particles'
              ? clamp(mappedGray + particleBoost, 0, 255)
              : mappedGray;
        const char = charFromGray(glyphGray, charset, x, y, cols, rows, edgeContrast);
        if (char === ' ') continue;
        const glyphColor = colorFromMode(r, g, b, glyphGray, x, y, cols, rows, edgeContrast);
        ctx.fillStyle = invertCell ? invertCssColor(glyphColor) : glyphColor;
        ctx.fillText(char, drawX, drawY);
      }
    }

    if (borderGlowStrength > 0.001) {
      drawBorderGlowOverlay(ctx, renderWidth, renderHeight, borderGlowStrength);
    }
    ctx.globalAlpha = 1;
    lastFrameDurationMs = Math.max(0, performance.now() - frameStartedAt);
    const fpsElapsed = now - fpsWindowStart;
    if (fpsElapsed >= 500) {
      const nextFps = Math.round((fpsFrameCount * 1000) / fpsElapsed);
      reportFps(Number.isFinite(nextFps) ? nextFps : 0, {
        chars: lastCharCount,
        frameMs: lastFrameDurationMs,
      });
      fpsFrameCount = 0;
      fpsWindowStart = now;
    }

    if (requiresContinuousRendering(interactionEnabled)) {
      scheduleRender();
    }
  }

  async function start() {
    resize();
    document.addEventListener('visibilitychange', handleDocumentVisibilityChange);
    window.addEventListener('resize', handleWindowResize);
    if (typeof IntersectionObserver === 'function') {
      const visibilityThreshold = clamp(Number(EXPORT_OPTIONS.visibilityThreshold ?? 0.01) || 0.01, 0, 1);
      intersectionObserver = new IntersectionObserver(handleIntersection, {
        threshold: [0, visibilityThreshold, 0.25],
      });
      intersectionObserver.observe(mount);
    }
    if (typeof ResizeObserver === 'function') {
      resizeObserver = new ResizeObserver(() => {
        resize();
        scheduleRender(true);
      });
      resizeObserver.observe(mount);
    }
    if (EXPORT_OPTIONS.enableInteractionEffects) {
      window.addEventListener('pointermove', handleWindowPointerMove, { passive: true });
      window.addEventListener('pointerdown', handleWindowPointerDown, { passive: true });
      window.addEventListener('blur', handleWindowBlur);
    }
    source = await loadSource();
    handleRenderActivityChange(true);
  }

  start().catch((error) => {
    reportFps(0);
    drawError('Export source failed: ' + (error && error.message ? error.message : 'Unknown error'));
  });

  window.__asciiDitherExportDestroy = function() {
    reportFps(0);
    if (rafId) cancelAnimationFrame(rafId);
    if (stream) stream.getTracks().forEach((track) => track.stop());
    document.removeEventListener('visibilitychange', handleDocumentVisibilityChange);
    window.removeEventListener('resize', handleWindowResize);
    if (intersectionObserver) intersectionObserver.disconnect();
    if (resizeObserver) resizeObserver.disconnect();
    if (sourceLoopHandler && source && typeof source.removeEventListener === 'function') {
      source.removeEventListener('ended', sourceLoopHandler);
      sourceLoopHandler = null;
    }
    window.removeEventListener('pointermove', handleWindowPointerMove);
    window.removeEventListener('pointerdown', handleWindowPointerDown);
    window.removeEventListener('blur', handleWindowBlur);
    mount.replaceChildren();
    delete mount.__asciiDitherDestroy;
    if (IS_TEMPLATE_PREVIEW_RUNTIME) {
      const runtimeEntry = runtimeScope[TEMPLATE_PREVIEW_RUNTIME_KEY];
      if (runtimeEntry && runtimeEntry.id === previewRuntimeId) {
        delete runtimeScope[TEMPLATE_PREVIEW_RUNTIME_KEY];
      }
    }
  };
  mount.__asciiDitherDestroy = window.__asciiDitherExportDestroy;
  if (IS_TEMPLATE_PREVIEW_RUNTIME) {
    const runtimeEntry = runtimeScope[TEMPLATE_PREVIEW_RUNTIME_KEY];
    if (runtimeEntry && runtimeEntry.id === previewRuntimeId) {
      runtimeEntry.destroy = window.__asciiDitherExportDestroy;
    }
  }
})();
