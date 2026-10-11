"""
Minimal S-expression reader/writer for KiCad files (symbol libraries, schematics).

KiCad's text formats are plain S-expressions: lists, bare atoms and double-quoted
strings with backslash escapes.  `parse` returns nested Python lists of `str` (atoms)
and `Q` (quoted strings, kept distinct so they are written back quoted).
"""
from __future__ import annotations


class Q(str):
    """A quoted string atom."""


def parse(text: str):
    i, n = 0, len(text)
    stack = [[]]
    while i < n:
        c = text[i]
        if c == "(":
            stack.append([])
            i += 1
        elif c == ")":
            node = stack.pop()
            stack[-1].append(node)
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while j < n:
                ch = text[j]
                if ch == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                if ch == '"':
                    break
                buf.append(ch)
                j += 1
            stack[-1].append(Q("".join(buf)))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in "()":
                j += 1
            stack[-1].append(text[i:j])
            i = j
    return stack[0]


def _atom(a) -> str:
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        s = f"{a:.4f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(a)


def dump(node, indent=0) -> str:
    """Pretty-print: short lists on one line, long ones broken per child."""
    if not isinstance(node, list):
        return _atom(node)
    flat = "(" + " ".join(dump(c) for c in node) + ")"
    if len(flat) <= 100 and "\n" not in flat:
        return flat
    pad = "  " * (indent + 1)
    head = [dump(c) for c in node[:2] if not isinstance(c, list)]
    rest = node[len(head):]
    out = "(" + " ".join(head)
    for c in rest:
        out += "\n" + pad + dump(c, indent + 1)
    return out + ")"


def find(node, key):
    """All direct children lists whose head atom is `key`."""
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key):
    r = find(node, key)
    return r[0] if r else None
