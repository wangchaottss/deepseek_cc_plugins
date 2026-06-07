#!/usr/bin/env node

/**
 * Claude Code Statusline — task-tracker project
 *
 * Output: [████░░░░] 42% 85K/200K | deepseek-v4-pro[1m] | /path/to/project
 */

const { stdin, stdout } = process;

let data = '';

stdin.setEncoding('utf8');
stdin.on('data', (chunk) => {
  data += chunk;
});

stdin.on('end', () => {
  let input;
  try {
    input = JSON.parse(data);
  } catch {
    stdout.write('\n');
    return;
  }

  const reset = '\x1b[0m';
  const dim = '\x1b[2m';
  const bold = '\x1b[1m';
  const green = '\x1b[32m';
  const yellow = '\x1b[33m';
  const red = '\x1b[31m';
  const cyan = '\x1b[36m';

  const ctx = input.context_window || {};

  // --- context usage -------------------------------------------------------

  const pct = ctx.used_percentage ?? null;

  const currentInput = ctx.current_usage?.input_tokens ?? 0;
  const currentCacheCreate = ctx.current_usage?.cache_creation_input_tokens ?? 0;
  const currentCacheRead = ctx.current_usage?.cache_read_input_tokens ?? 0;
  const effectiveUsage = currentInput + currentCacheCreate + currentCacheRead;

  const totalInput = ctx.total_input_tokens ?? 0;
  const windowSize = ctx.context_window_size ?? 200000;

  // --- progress bar ---------------------------------------------------------

  const barWidth = 8;
  let barColor = dim;
  let bar;
  let pctDisplay;

  if (pct === null) {
    bar = dim + '▁'.repeat(barWidth) + reset;
    pctDisplay = dim + '--' + reset;
  } else {
    if (pct >= 80) barColor = red;
    else if (pct >= 50) barColor = yellow;
    else barColor = green;

    const filled = Math.max(0, Math.min(barWidth, Math.round((pct / 100) * barWidth)));
    bar =
      barColor +
      '█'.repeat(filled) +
      dim +
      '░'.repeat(barWidth - filled) +
      reset;

    pctDisplay = barColor + bold + pct.toFixed(0).padStart(3) + '%' + reset;
  }

  // --- token count ----------------------------------------------------------

  const fmtTokens = (n) => {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 10_000) return (n / 1_000).toFixed(0) + 'K';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
    return String(n);
  };

  const usedStr = effectiveUsage > 0 ? fmtTokens(effectiveUsage) : fmtTokens(totalInput);
  const maxStr = fmtTokens(windowSize);

  // --- model ----------------------------------------------------------------
  // model may be a string or an object like { name: "...", display_name: "..." }
  let model = input.model || '?';
  if (typeof model === 'object' && model !== null) {
    model = model.name || model.id || model.display_name || '?';
  }

  // --- cwd ------------------------------------------------------------------

  let cwd = input.cwd || '';
  // Shorten to just the last 2 path segments for readability
  if (cwd) {
    const home = process.env.HOME || '';
    if (home && cwd.startsWith(home + '/')) {
      cwd = '~/' + cwd.slice(home.length + 1);
    }
  }

  // --- build output ---------------------------------------------------------

  const parts = [];

  // Context usage: [████░░░░] 42% 85K/200K
  parts.push(bar + ' ' + pctDisplay + ' ' + dim + usedStr + '/' + maxStr + reset);

  // Model
  parts.push(cyan + model + reset);

  // Current directory
  if (cwd) {
    parts.push(dim + cwd + reset);
  }

  stdout.write(parts.join(' ' + dim + '|' + reset + ' ') + '\n');
});
