"""Cheap, deterministic language contract shared by REST and MCP."""
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from collections import Counter
from langdetect import DetectorFactory, detect_langs, LangDetectException
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)
LANG_NAMES = {"zh-TW": "Traditional Chinese", "zh-CN": "Simplified Chinese", "en": "English",
              "ja": "Japanese", "fr": "French", "es": "Spanish", "ru": "Russian",
              "ko": "Korean", "de": "German"}
ALIASES = {"zh": "zh-TW", "zh-tw": "zh-TW", "zh-hant": "zh-TW", "zh-hk": "zh-TW",
           "zh-cn": "zh-CN", "zh-hans": "zh-CN"}


def normalize_language(value: str | None, *, auto=False) -> str:
    if not value or value.lower() == "auto":
        if auto:
            return "auto"
        raise ValueError("A language code is required")
    value = value.strip().replace("_", "-").lower()
    value = ALIASES.get(value, value.split("-")[0])
    if value not in LANG_NAMES:
        raise ValueError("Unsupported language code")
    return value


def source_languages(values: list[str] | None) -> list[str]:
    return list(dict.fromkeys(normalize_language(v) for v in values or []))


def detect(text: str) -> str | None:
    text = re.sub(r"https?://\S+|`[^`]*`", " ", text)[:4000]
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 8:
        return None
    # Mixed CJK questions containing a single English acronym remain CJK.
    kana = len(re.findall(r"[\u3040-\u30ff]", text))
    han = len(re.findall(r"[\u3400-\u9fff]", text))
    if kana >= 2 and (kana + han) / len(letters) > 0.4:
        return "ja"
    if han >= 6 and han / len(letters) > 0.45 and not kana:
        return "zh-TW"
    if not han and not kana and len(re.findall(r'[^\W\d_]+', text, flags=re.UNICODE)) < 3:
        return None
    try:
        scores = detect_langs(text)
        second = scores[1].prob if len(scores) > 1 else 0
        if scores[0].prob < 0.85 or scores[0].prob - second < 0.25:
            return None
        return normalize_language(scores[0].lang)
    except (LangDetectException, ValueError):
        return None



LANGUAGE_TERMS = {
    "zh-TW": r"繁體中文|繁体中文|traditional Chinese|中文",
    "zh-CN": r"简体中文|簡體中文|simplified Chinese",
    "en": r"英文|英語|英语|English|anglais|inglés",
    "ja": r"日文|日語|日语|Japanese|日本語",
    "fr": r"法文|法語|法语|French|français",
    "es": r"西班牙文|西班牙語|Spanish|español",
    "ru": r"俄文|俄語|Russian|русском",
    "ko": r"韓文|韓語|Korean|한국어",
    "de": r"德文|德語|German|Deutsch",
}


def explicit_instruction(text: str) -> str | None:
    # Only affirmative answer-language directives; ignore quoted examples.
    text = re.sub(r'`[^`]*`|"[^"]*"|「[^」]*」|“[^”]*”', "", text)
    matches = []
    for code, term in LANGUAGE_TERMS.items():
        patterns = [rf"(?:請|请)?(?:用|以|使用)\s*(?:{term})\s*(?:回答|回覆|回复|作答|說明|说明)",
                    rf"(?:answer|respond|reply|write)\s+(?:only\s+)?in\s+(?:{term})\b",
                    rf"(?:{term})で(?:回答|答えて)"]
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                before = text[max(0, match.start() - 16):match.start()].lower()
                if re.search(r"(?:不要|別|别|勿|not|don't|never)\s*$", before):
                    continue
                matches.append((match.start(), code))
    return max(matches)[1] if matches else None


@dataclass(frozen=True)
class ResolvedLanguage:
    language: str
    source: str


def resolve(question: str, response_language: str | None = "auto",
            interface_language: str | None = None, preferred_language: str | None = None,
            recent_languages: list[str] | None = None) -> ResolvedLanguage:
    requested = normalize_language(response_language, auto=True)
    preferred = normalize_language(preferred_language, auto=True)
    fallback = normalize_language(interface_language or "zh-TW")
    recent = [normalize_language(v) for v in (recent_languages or [])[-5:]]
    if requested != "auto":
        result = ResolvedLanguage(requested, "explicit")
    elif instruction := explicit_instruction(question):
        result = ResolvedLanguage(instruction, "explicit")
    elif preferred != "auto":
        result = ResolvedLanguage(preferred, "explicit")
    elif detected := detect(question):
        result = ResolvedLanguage(detected, "detected")
    else:
        counts = Counter(recent)
        stable = counts.most_common(1)[0][0] if counts else fallback
        result = ResolvedLanguage(stable, "fallback")
    logger.info("response_language=%s language_source=%s", result.language, result.source)
    return result
