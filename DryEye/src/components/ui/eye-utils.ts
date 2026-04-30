export type EyeState = '睁眼' | '闭眼' | '频繁眨眼' | '慢速眨眼' | '正常眨眼';

export const eyeStateLabels: Record<EyeState, string> = {
  '睁眼': '睁眼',
  '闭眼': '闭眼',
  '频繁眨眼': '频繁眨眼',
  '慢速眨眼': '慢速眨眼',
  '正常眨眼': '正常眨眼',
};

export const eyeStateDescriptions: Record<EyeState, string> = {
  '睁眼': '双眼处于睁开状态，状态正常',
  '闭眼': '双眼处于闭合状态，请注意',
  '频繁眨眼': '眨眼频率过高，可能存在眼部不适',
  '慢速眨眼': '眨眼动作缓慢，可能存在干眼风险',
  '正常眨眼': '眨眼频率正常，眼部状态良好',
};

export const normalizeEyeState = (
  state: string | undefined,
): EyeState => {
  if (typeof state !== 'string') return '正常眨眼';
  const s = state.trim();
  if (!s) return '正常眨眼';

  if (s === '睁眼' || s === '闭眼' || s === '频繁眨眼' || s === '慢速眨眼' || s === '正常眨眼') return s as EyeState;

  const normalized = s.toLowerCase().replace(/\s+/g, '_');
  if (normalized === 'open' || normalized === 'opened' || normalized === 'eye_open') return '睁眼';
  if (normalized === 'close' || normalized === 'closed' || normalized === 'eye_close' || normalized === 'eye_closed') return '闭眼';
  if (
    normalized === 'fast_blink' ||
    normalized === 'frequent_blink' ||
    normalized === 'blink_fast' ||
    normalized === 'rapid_blink' ||
    normalized === 'closing'
  ) return '频繁眨眼';
  if (normalized === 'slow_blink' || normalized === 'blink_slow' || normalized === 'slowblink') return '慢速眨眼';
  if (normalized === 'normal' || normalized === 'normal_blink' || normalized === 'blink_normal') return '正常眨眼';

  return '正常眨眼';
};
