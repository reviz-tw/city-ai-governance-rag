/** UTF-16 offsets that keep Unicode code points and citation markers intact. */
export function answerRevealOffsets(content: string, start: number, streaming = false): number[] {
  const suffix = content.slice(start);
  // Show the section heading at once, then reveal its body.
  const heading = suffix.match(/^\s*#{1,3} [^\n]+\n/);
  let offset = start + (heading?.[0].length || 0);
  const offsets = [offset];
  let body = content.slice(offset);
  // A provider fragment can end inside a citation or Unicode surrogate pair.
  if (streaming) body = body.replace(/\[[^\]\n]*$/, '').replace(/[\uD800-\uDBFF]$/, '');
  for (const token of body.matchAll(/\[[^\]\n]*\]|\*\*|[\s\S]/gu)) {
    offset += token[0].length;
    offsets.push(offset);
  }
  return offsets;
}

/** Advance only unread text; catch up with bursts without replaying earlier chunks. */
export function advanceAnswerReveal(offsets: number[], current: number, elapsedMs: number): number {
  const next = offsets.findIndex(offset => offset > current);
  if (next < 0) return current;
  const pending = offsets.length - next;
  const count = Math.max(1, Math.ceil(Math.max(0, elapsedMs) * Math.max(0.06, pending / 600)));
  return offsets[Math.min(offsets.length - 1, next + count - 1)];
}

export function shouldFollowAnswer(message?: {stage?: string; detailedStart?: number}) {
  // Retain the reading position through waiting, reveal, completion and errors.
  return message?.stage !== 'expanding' && message?.detailedStart === undefined;
}
