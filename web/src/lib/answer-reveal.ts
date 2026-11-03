/** UTF-16 offsets that keep Unicode code points and citation markers intact. */
export function answerRevealOffsets(content: string, start: number): number[] {
  const suffix = content.slice(start);
  // Show the section heading at once, then reveal its body.
  const heading = suffix.match(/^\s*#{1,3} [^\n]+\n/);
  let offset = start + (heading?.[0].length || 0);
  const offsets = [offset];
  for (const token of content.slice(offset).matchAll(/\[[^\]\n]*\]|\*\*|[\s\S]/gu)) {
    offset += token[0].length;
    offsets.push(offset);
  }
  return offsets;
}

export function shouldFollowAnswer(message?: {stage?: string; detailedStart?: number}) {
  // Retain the reading position through waiting, reveal, completion and errors.
  return message?.stage !== 'expanding' && message?.detailedStart === undefined;
}
