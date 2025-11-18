# parser.py
import re
from collections import defaultdict

TAG_PATTERN = re.compile(r"<s_([a-zA-Z0-9_]+)>(.*?)</s_\1>", re.DOTALL)

def parse_donut_output(text: str):
    """
    Parse nested Donut (CORD-v2) markup into structured Python dict.
    """
    def _parse_section(section_text: str):
        data = defaultdict(list)
        for tag, inner in TAG_PATTERN.findall(section_text):
            if "<s_" in inner:
                data[tag].append(_parse_section(inner))
            else:
                value = inner.strip()
                if value:
                    data[tag].append(value)
        return {k: v[0] if len(v) == 1 else v for k, v in data.items()}

    parsed = _parse_section(text)
    return parsed or {"raw_output": text}
