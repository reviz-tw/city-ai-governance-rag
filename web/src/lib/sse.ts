export async function* readSSE(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let completed = false;
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n/g, '\n');
      let boundary: number;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const payload = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n');
        if (!payload) continue;
        const event = JSON.parse(payload);
        if (event.type === 'done') completed = true;
        yield event;
      }
      if (done) break;
    }
    if (!completed || buffer.trim()) throw new Error('The response stream ended before completion. Please retry.');
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}
