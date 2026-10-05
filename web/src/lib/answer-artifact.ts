import {ChatMessage} from '../types';

// Share the accepted marker syntax between source selection and visible links.
export const CITATION_MARKER = /\[(?:citation:\s*)?\d+(?:\s*,\s*(?:citation:\s*)?\d+)*\]/gi;

export function citationIds(marker: string): number[] {
  if (!new RegExp(`^(?:${CITATION_MARKER.source})$`, 'i').test(marker)) return [];
  return marker.slice(1, -1).replace(/citation:\s*/gi, '').split(',').map(value => Number(value.trim()));
}

/** Every output is bound to the answer whose action the reader clicked. */
export function answerEvidence(message: ChatMessage) {
  const cited = new Set([...message.content.matchAll(CITATION_MARKER)].flatMap(match=>citationIds(match[0])));
  const citations = (message.citations || []).filter(c=>cited.has(c.citation_id));
  const source_ids = [...new Set(citations.flatMap(c => c.document_id ? [c.document_id] : []))];
  const source_passages: Record<string,string[]> = {};
  for (const id of source_ids) {
    const related = citations.filter(c=>c.document_id===id);
    // Older citations without locations retain the API's whole-original fallback.
    if (related.every(c=>c.block_ids?.length)) source_passages[id] = [...new Set(related.flatMap(c=>c.block_ids!))];
  }
  return {scope:'answer', message_ids:[message.id], source_ids, source_passages, context:message.content.slice(0,6000)};
}
