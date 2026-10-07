"""@package tests.test_integration_sexpr
@brief Checks bounded parsing and exact string/atom semantics for KiCad trees.
@details Native compatibility is verified separately during actual staging.
"""

import pytest

from partsmith.integration.sexpr import parse, serialize, table_entries


def test_tree_roundtrip_preserves_exact_decimal_and_strings():
    """@brief Preserves quoted engineering values and exact geometry spelling.
    @return None.
    @details Serialization changes whitespace without changing a parsed tree.
    """
    blob = b'(footprint "part" (pad "1" smd (at -0.500001 1.200001)))\n'
    tree = parse(blob)
    assert parse(serialize(tree)) == tree
    assert b'"1"' in serialize(tree) and b"-0.500001" in serialize(tree)


@pytest.mark.parametrize(
    "blob",
    [
        b"",
        b"()",
        b"(root",
        b"(root))",
        b"(x)(y)",
        b'(root "unfinished)',
        b"atom",
        b"(root ())",
    ],
)
def test_malformed_trees_fail_closed(blob):
    """@brief Rejects incomplete or ambiguous KiCad trees before comparison.
    @param blob Exact malformed fixture bytes.
    @return None.
    @details Invalid tokenization is never normalized into valid engineering.
    """
    with pytest.raises(ValueError):
        parse(blob)


def test_excessive_nesting_fails():
    """@brief Bounds parser recursion independently of file-byte limits.
    @return None.
    @details Deeply nested content cannot bypass the versioned parser profile.
    """
    with pytest.raises(ValueError, match="nesting"):
        parse(b"(x " * 65 + b")" * 65)


@pytest.mark.parametrize(
    "blob",
    [
        b"(fp_lib_table)",
        b'(sym_lib_table (lib (name "x")))',
        b'(sym_lib_table (lib (name "x") (uri "a")) '
        b'(lib (name "X") (uri "b")))',
        b'(sym_lib_table (lib (name "x") (uri (invalid))))',
        b'(sym_lib_table (lib (name "x") (uri "")))',
    ],
)
def test_table_type_and_namespace_failures(blob):
    """@brief Rejects wrong table scope, missing URI and nickname aliases.
    @param blob Malformed or conflicting table fixture.
    @return None.
    @details Complete unrelated entry nodes remain available for preservation.
    """
    with pytest.raises(ValueError):
        table_entries(blob, "sym_lib_table")
