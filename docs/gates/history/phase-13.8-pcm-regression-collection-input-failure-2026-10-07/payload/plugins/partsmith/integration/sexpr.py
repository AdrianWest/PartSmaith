"""@package partsmith.integration.sexpr
@brief Parses bounded KiCad trees while preserving atom and string spelling.
@details Native parsing is separately mandatory; this parser checks exact
semantic trees and project-local table namespace declarations.
"""

import json
import re
import unicodedata

from partsmith.integration.policy import ResourcePolicy


class Atom(str):
    """@brief Distinguishes unquoted KiCad tokens from quoted strings.
    @details Geometry numbers remain exact text rather than binary floats.
    """


def parse(blob: bytes) -> list:
    """@brief Parses exactly one bounded UTF-8 KiCad S-expression tree.
    @param blob Exact input bytes.
    @return Nested list containing atoms and quoted strings.
    @details Rejects incomplete strings, roots and excessive depth/token count.
    """
    ResourcePolicy().require_sizes([len(blob)])
    text = blob.decode("utf-8", errors="strict")
    stack, roots = [], []
    count = 0
    for match in re.finditer(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text):
        count += 1
        if count > 1_000_000:
            raise ValueError("KiCad token limit")
        token = match.group()
        if token == "(":
            if len(stack) >= 64:
                raise ValueError("KiCad nesting limit")
            node = []
            (stack[-1] if stack else roots).append(node)
            stack.append(node)
        elif token == ")":
            if not stack or not stack[-1]:
                raise ValueError("Unbalanced or empty KiCad node")
            stack.pop()
        elif not stack or '"' in token and not token.startswith('"'):
            raise ValueError("Invalid KiCad token")
        elif token.startswith('"'):
            stack[-1].append(json.loads(token))
        else:
            stack[-1].append(Atom(token))
    if stack or len(roots) != 1:
        raise ValueError("Expected one complete KiCad root")
    return roots[0]


def serialize(tree: list) -> bytes:
    """@brief Serializes a bounded tree with stable atom/string distinctions.
    @param tree Exact parsed or explicitly constructed semantic tree.
    @return Deterministic UTF-8 bytes with LF ending.
    @details Preserves numeric text and engineering values without rounding.
    """

    def render(node, depth: int) -> str:
        """@brief Renders one bounded tree element.
        @param node Nested list, atom or quoted string.
        @param depth Current traversal depth.
        @return Exact deterministic spelling.
        @details Unknown types and excessive depth fail explicitly.
        """
        if depth > 64:
            raise ValueError("KiCad nesting limit")
        if isinstance(node, list):
            if not node:
                raise ValueError("Empty KiCad node")
            return "(" + " ".join(render(n, depth + 1) for n in node) + ")"
        if isinstance(node, Atom):
            if not node or re.search(r'[\s()"\\]', node):
                raise ValueError("Invalid KiCad atom")
            return str(node)
        if isinstance(node, str):
            return json.dumps(node, ensure_ascii=False)
        raise ValueError("Invalid KiCad tree type")

    result = (render(tree, 0) + "\n").encode("utf-8")
    ResourcePolicy().require_sizes([len(result)])
    return result


def children(tree: list, name: str) -> list[list]:
    """@brief Selects immediate nodes with one exact atom tag.
    @param tree Parsed tree.
    @param name Requested node tag.
    @return Immediate matching child lists.
    @details Does not recursively select inherited or unrelated entries.
    """
    return [n for n in tree[1:] if isinstance(n, list) and n and n[0] == name]


def table_entries(blob: bytes, kind: str) -> dict[str, list]:
    """@brief Verifies one complete project-local library table namespace.
    @param blob Exact table bytes.
    @param kind Expected sym_lib_table or fp_lib_table root.
    @return Nickname to complete entry node mapping.
    @details Duplicate/case aliases and malformed name/URI fields fail closed.
    """
    root = parse(blob)
    if root[0] != kind:
        raise ValueError("Wrong KiCad library table")
    entries, aliases = {}, set()
    for entry in children(root, "lib"):
        names, uris = children(entry, "name"), children(entry, "uri")
        if len(names) != 1 or len(uris) != 1:
            raise ValueError("Incomplete library table entry")
        if len(names[0]) != 2 or len(uris[0]) != 2:
            raise ValueError("Malformed library table entry")
        name, uri = names[0][1], uris[0][1]
        if (
            not isinstance(name, str)
            or not name
            or unicodedata.normalize("NFC", name) != name
            or name.casefold() in aliases
            or any(ord(character) < 32 for character in name)
        ):
            raise ValueError("Library nickname collision")
        if (
            not isinstance(uri, str)
            or not uri
            or any(ord(character) < 32 for character in uri)
        ):
            raise ValueError("Malformed library URI")
        aliases.add(name.casefold())
        entries[name] = entry
    return entries
