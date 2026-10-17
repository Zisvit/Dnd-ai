#!/usr/bin/env python3
import sys
import re
import time
from .config import TERM_WIDTH, OUTPUT_DELAY
from .colors import RESET

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def _write(text):
    sys.stdout.buffer.write(text.encode('utf-8', errors='replace'))
    sys.stdout.buffer.flush()

def wrap_ansi(text, width):
    if width < 10:
        width = 40
    lines = []
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        if not paragraph:
            lines.append('')
            continue
        visible = ANSI_ESCAPE.sub('', paragraph)
        if len(visible) <= width:
            lines.append(paragraph)
            continue
        parts = re.split(r'(\s+)', paragraph)
        current_line = ''
        current_len = 0
        for i in range(0, len(parts), 2):
            word = parts[i] if i < len(parts) else ''
            space = parts[i+1] if i+1 < len(parts) else ''
            word_visible = ANSI_ESCAPE.sub('', word)
            space_visible = ANSI_ESCAPE.sub('', space) if space else ''
            word_len = len(word_visible)
            space_len = len(space_visible)
            if current_len + word_len > width and current_len > 0:
                lines.append(current_line.rstrip())
                current_line = word + space
                current_len = word_len + space_len
            else:
                current_line += word + space
                current_len += word_len + space_len
        if current_line.strip():
            lines.append(current_line.rstrip())
    return '\n'.join(lines)


def slow_print(text, delay=OUTPUT_DELAY):
    if not text:
        return
    if not text.endswith(RESET):
        text += RESET
    wrapped = wrap_ansi(text, TERM_WIDTH)
    if delay <= 0:
        _write(wrapped + '\n')
        return
    lines = wrapped.split('\n')
    for line_idx, line in enumerate(lines):
        if not line:
            _write('\n')
            continue
        parts = re.split(r'(\x1B\[[0-9;]*[a-zA-Z])', line)
        for part in parts:
            if re.match(r'\x1B\[[0-9;]*[a-zA-Z]', part):
                _write(part)
            else:
                for ch in part:
                    _write(ch)
                    time.sleep(delay)
        if line_idx < len(lines) - 1:
            _write('\n')
    _write('\n')


_JUNK_PATTERNS = [
    re.compile(r'^\s*(?:\d+\.?\s+)?\*\*[^*]+\*\*[:—]?\s*$', re.I),
    re.compile(r'^\s*[-•]\s+\*\*[^*]+\*\*[:—]?', re.I),
    re.compile(r'^\s*(?:#|##|###)\s+'),
    re.compile(r'^\s*Proceeds?\.\s*$', re.I),
    re.compile(r'^\s*✅\s*$'),
    re.compile(r'^\s*\[Done\]\s*$', re.I),
    re.compile(r'^\s*Output matches.*$', re.I),
    re.compile(r'^\s*Self-Correction.*$', re.I),
    re.compile(r'^\s*Check(?:ed)?\s+Against.*$', re.I),
    re.compile(r'^\s*Draft Construction.*$', re.I),
    re.compile(r'^\s*Final Polish.*$', re.I),
    re.compile(r'^\s*Proceed\.?\s*$', re.I),
    re.compile(r'^\s*Analyze User Input.*$', re.I),
    re.compile(r'^\s*Deconstruct Requirements.*$', re.I),
    re.compile(r'^\s*Brainstorming.*$', re.I),
    re.compile(r'^\s*Mental Refinement.*$', re.I),
    re.compile(r'^\s*Ready\.\s*Proceeds?\.\s*$', re.I),
    re.compile(r'^\s*Ready\.\s*$', re.I),
    re.compile(r'^\s*[-•]\s+[A-Z][a-z]+.*:\s*$', re.I),
    re.compile(r'^\s*[-•]\s+\d+.*$', re.I),
    re.compile(r'^\s*[-•]\s+(?:User|Need|Must|Should|Can|Will|Use|Keep|End|Start|Make|Write|Describe|Include|Ensure|Check|Verify|Follow|Add|Remove|Change|Update|Fix|Improve|Adjust|Refine|Polish|Review|Test|Validate|Confirm|Opening|Sights|Sounds|NPC|Integration|Ending|Tone|Draft|Check|Self).*$', re.I),
]


def clean(text):
    if not text:
        return ''
    text = ANSI_ESCAPE.sub('', text)

    text = re.sub(r'<think>[\s\S]*?</think>', '', text)
    text = re.sub(r'<think>[\s\S]*?\n\n', '\n', text)
    text = re.sub(r'<think>[\s\S]*', '', text)
    text = re.sub(r'<reasoning>[\s\S]*?</reasoning>', '', text)
    text = re.sub(r'<𝑎𝑛𝑡𝑚𝑙:thinking>[\s\S]*?</𝑎𝑛𝑡𝑚𝑙:thinking>', '', text)
    text = re.sub(r'<𝑎𝑛𝑡𝑚𝑙:thinking>[\s\S]*?<𝑎𝑛𝑡𝑚𝑙:thinking>', '', text)
    text = re.sub(r'<𝑎𝑛𝑡𝑚𝑙:thinking>[\s\S]*?\n\n', '\n', text)
    text = re.sub(r'<𝑎𝑛𝑡𝑚𝑙:thinking>[\s\S]*', '', text)
    text = re.sub(r'</𝑎𝑛𝑡𝑚𝑙:thinking>', '', text)
    text = re.sub(r'<thinking>[\s\S]*?</thinking>', '', text)
    text = re.sub(r'<thinking>[\s\S]*?<thinking>', '', text)
    text = re.sub(r'<thinking>[\s\S]*?\n\n', '\n', text)
    text = re.sub(r'<thinking>[\s\S]*', '', text)
    text = re.sub(r'</thinking>', '', text)

    text = re.sub(r'Here[\s\S]{0,30}thinking process[:\s]*\n?', '', text, flags=re.IGNORECASE)

    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            clean_lines.append('')
            continue
        skip = False
        for pat in _JUNK_PATTERNS:
            if pat.match(stripped):
                skip = True
                break
        if not skip:
            clean_lines.append(line)

    text = '\n'.join(clean_lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# ── Потоковый вывод с подавлением thinking-тегов ───────────────────────────

_THINK_OPEN_RE = re.compile('<𝑎𝑛𝑡𝑚𝑙:thinking>|<thinking>|<think>')
_THINK_CLOSE_RE = re.compile('</𝑎𝑛𝑡𝑚𝑙:thinking>|</thinking>|</think>')
_THINK_ANY_RE = re.compile(
    '</?𝑎𝑛𝑡𝑚𝑙:thinking>|</?thinking>|</?think>')
_MAX_TAG_LEN = 17

# Все возможные префиксы opening-тегов (для detection split-тегов на границе чанков)
_OPEN_TAG_LIST = ['<𝑎𝑛𝑡𝑚𝑙:thinking>', '<thinking>', '<think>']
_OPEN_PREFIXES = set()
for _t in _OPEN_TAG_LIST:
    for _i in range(1, len(_t) + 1):
        _OPEN_PREFIXES.add(_t[:_i])


class StreamingPrinter:
    """Печатает токены по мере поступления, скрывая thinking-теги."""

    def __init__(self):
        self._buf = ''
        self._in_think = False
        self._printed = False

    def on_token(self, token):
        if not token:
            return
        self._buf += token
        self._process()

    def _process(self):
        while self._buf:
            if self._in_think:
                m = _THINK_CLOSE_RE.search(self._buf)
                if m:
                    self._buf = self._buf[m.end():]
                    self._in_think = False
                else:
                    if len(self._buf) > _MAX_TAG_LEN:
                        cut = len(self._buf) - _MAX_TAG_LEN
                        self._buf = self._buf[cut:]
                    return
            else:
                m = _THINK_OPEN_RE.search(self._buf)
                if m:
                    before = self._buf[:m.start()]
                    if before:
                        self._flush(before)
                    self._buf = self._buf[m.end():]
                    self._in_think = True
                else:
                    safe_end = len(self._buf)
                    for plen in range(min(_MAX_TAG_LEN, len(self._buf)), 1, -1):
                        if self._buf[-plen:] in _OPEN_PREFIXES:
                            safe_end = len(self._buf) - plen
                            break
                    if safe_end > 0:
                        self._flush(self._buf[:safe_end])
                        self._buf = self._buf[safe_end:]
                    return

    def _flush(self, text):
        if text:
            self._printed = True
            _write(text)

    def finish(self):
        if self._in_think:
            self._buf = ''
            self._in_think = False
        elif self._buf:
            self._flush(self._buf)
            self._buf = ''
        if self._printed:
            _write('\n')
