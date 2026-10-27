/** Presentation only: never write cleaned text back to documents or citations. */
export function sourceDisplayText(text: string): string {
  return text.replace(/\r\n?/g, '\n').split('\n')
    .map(line => line.replace(/[\t\f\v\u00a0\u3000 ]+/g, ' ').trim())
    // Markdown table rules carry no source content. Keep every data row/cell.
    .filter(line => !/^\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?$/.test(line))
    .join('\n').replace(/\n{3,}/g, '\n\n').trim();
}
