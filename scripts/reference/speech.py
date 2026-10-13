"""Reference implementation of looking up a spoken line: BoothEnv.getSpeech and
the data.Speech constructor, as far as their random draws and resulting text
go (docs/speech.md).

Every stock response that has a candidate line costs one draw from the
booth's generator, each `$other-response` word inside the chosen line costs
its own, and a text with `;` alternatives costs one more.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tabtree  # noqa: E402
import travspec as T  # noqa: E402

EXPRESSION = re.compile(r"^(.*?)(==|!=|<=|>=|<|>)(.*)$")


class SpeechLib:
    def __init__(self, speeches_text):
        self.responses = {}
        for entry in tabtree.parse(speeches_text).nodes:
            lines = []
            for child in entry.nodes:
                words = list(child.params)
                value = when = None
                if words and words[0].startswith("="):
                    value = words.pop(0)[1:]
                if words and words[0].startswith("?"):
                    when = words.pop(0)[1:]
                lines.append((value, when, " ".join(words)))
            self.responses[entry.params[0]] = (entry.params[1] if len(entry.params) > 1 else None, lines)


def get_speech(lib, rand, fact_text, response_id, override_path=None):
    """Returns the text spoken (None when nothing is said). `fact_text(path)`
    gives a fact's current text, "" when unset."""
    if response_id is None:
        response_id = "default"
    if response_id.startswith("$") and not response_id.startswith("${"):
        response_id = response_id[1:]
    if response_id not in lib.responses:
        return _make(rand, response_id)                       # literal text
    path, lines = lib.responses[response_id]
    path = override_path if override_path is not None else path
    value = fact_text(path) if path is not None else ""
    candidates = []
    for line_value, when, text in lines:
        if line_value is not None and line_value != value:
            continue
        if when is not None:
            match = EXPRESSION.match(when)
            if not match or not T.test_one(match.group(1), match.group(2), match.group(3), fact_text):
                continue
        candidates.append(text)
    if not candidates:
        return None
    index = int(len(candidates) * rand.random())
    text = candidates[index] if index < len(candidates) else ""
    position = 0
    while True:                                               # $other-response words, left to right
        start = text.find("$", position)
        if start < 0:
            break
        end = start
        while end < len(text) and not text[end].isspace():
            end += 1
        inner = get_speech(lib, rand, fact_text, text[start:end], override_path) or ""
        text = text[:start] + inner + text[end:]
        position = start + len(inner)
    return _make(rand, text)


def _make(rand, text):
    """The Speech constructor's draw: one for `;` alternatives."""
    if ";" in text:
        parts = [part.strip() for part in text.split(";")]
        index = int(len(parts) * rand.random())
        text = parts[index] if index < len(parts) else ""
    return text
