"""Conservative, deterministic PDF reflow. Original extraction stays immutable."""
import re


_NEWLINE = r'(?:\r\n|\r(?!\n)|(?<!\r)\n)'
_BREAK = re.compile(r'[ \t]*' + _NEWLINE + r'[ \t]*')
_PARAGRAPH = re.compile(_NEWLINE + r'[ \t]*(?:' + _NEWLINE + r'[ \t]*)+')
_ITEM = re.compile(r'^(?:[-*+•●▪◦‧]\s*|\d+[.)、]\s*|[（(][\d一二三四五六七八九十]+[）)]|[一二三四五六七八九十]+[、.]|第[\d一二三四五六七八九十百]+[章節條]|#{1,6}\s|>)')
_CJK = re.compile(r'[\u2e80-\u9fff\uf900-\ufaff\uac00-\ud7af]')


def reflow(text: str) -> tuple[str, list[int]]:
    """Return readable text and each output character's offset in the original.

    Only layout whitespace changes. Blank paragraphs, sentence endings, list
    items, tables and code remain separate. Hyphens and all non-whitespace text
    are preserved; ambiguous table/code layouts are left untouched.
    """
    if '```' in text or '~~~' in text:
        return text, list(range(len(text)))
    output, offsets = [], []

    def original(start, end):
        output.append(text[start:end])
        offsets.extend(range(start, end))

    def separator(value, start):
        output.append(value)
        offsets.extend([start] * len(value))

    def paragraph(start, end):
        value = text[start:end]
        lines = value.splitlines()
        columns = sum(bool(re.search(r'\S[ \t]{2,}\S', line)) for line in lines)
        if '\t' in value or '|' in value or columns >= 2:
            original(start, end)
            return
        breaks = list(_BREAK.finditer(value))
        cursor = 0
        for index, match in enumerate(breaks):
            previous = value[cursor:match.start()].strip()
            following_end = breaks[index + 1].start() if index + 1 < len(breaks) else len(value)
            following = value[match.end():following_end].strip()
            original(start + cursor, start + match.start())
            # Short standalone labels/headings have insufficient evidence to join.
            heading = len(previous) < 24 and not re.search(r'[，,；;。!?！？]', previous)
            if previous.endswith('-'):
                heading = False
            preserve = (not previous or not following or heading or
                        bool(_ITEM.match(following)) or previous.endswith(('。', '！', '？', '.', '!', '?', ':', '：', ';', '；')))
            if preserve:
                join = '\n'
            elif previous.endswith('-') and following[0].islower():
                join = ''
            elif (_CJK.match(following[0]) and (_CJK.match(previous[-1]) or previous[-1] in '，、；：（「『')):
                join = ''
            elif following[0] in '，。！？、；：）」』】':
                join = ''
            else:
                join = ' '
            separator(join, start + match.start())
            cursor = match.end()
        original(start + cursor, end)

    cursor = 0
    for match in _PARAGRAPH.finditer(text):
        paragraph(cursor, match.start())
        separator('\n\n', match.start())
        cursor = match.end()
    paragraph(cursor, len(text))
    return ''.join(output), offsets
