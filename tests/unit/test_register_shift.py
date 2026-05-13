"""Unit tests for puma.perturbations.register_shift.

Formal-to-informal register substitution on technical text. Used in
place of a dialect perturbation when the corpus is monolingual
technical English without dialectal variation.

Reference:
    Tatman, R. (2017). Gender and dialect bias in YouTube's automatic
    captions. In Proceedings of the First ACL Workshop on Ethics in
    Natural Language Processing.
"""

from __future__ import annotations

import pytest

from puma.perturbations.register_shift import FORMAL_TO_INFORMAL, apply


@pytest.mark.unit
class TestSubstitution:
    def test_substitutes_known_formal_phrase(self) -> None:
        # Pick a phrase known to be in the mapping
        formal_phrase = next(iter(FORMAL_TO_INFORMAL))
        text = f"The system {formal_phrase} when the load spikes."
        out = apply(text)
        assert formal_phrase not in out
        assert FORMAL_TO_INFORMAL[formal_phrase] in out

    def test_substitutes_multiple_phrases_in_same_text(self) -> None:
        keys = list(FORMAL_TO_INFORMAL.keys())
        if len(keys) >= 2:
            text = f"Service {keys[0]} and database {keys[1]} simultaneously."
            out = apply(text)
            assert FORMAL_TO_INFORMAL[keys[0]] in out
            assert FORMAL_TO_INFORMAL[keys[1]] in out


@pytest.mark.unit
class TestPreservation:
    def test_text_without_formal_phrases_unchanged(self) -> None:
        text = "xyz qrs tuv 12345 nothing matches here"
        assert apply(text) == text

    def test_empty_text_returns_empty(self) -> None:
        assert apply("") == ""


@pytest.mark.unit
class TestIdempotence:
    def test_double_application_does_not_double_substitute(self) -> None:
        """Once 'exhausted'→'dying', a second pass must not touch 'dying'."""
        formal_phrase = next(iter(FORMAL_TO_INFORMAL))
        text = f"Pool {formal_phrase}."
        once = apply(text)
        twice = apply(once)
        # Idempotent in the sense that the second pass finds no more matches
        # — and only that. (A literal-equality check would also require that
        # the informal form is not itself a key in the dict, which the
        # implementation guarantees by construction.)
        assert twice == once


@pytest.mark.unit
class TestMappingShape:
    def test_mapping_non_empty(self) -> None:
        assert FORMAL_TO_INFORMAL

    def test_no_substitution_value_is_also_a_key(self) -> None:
        """Guard against cascading rewrites that would break idempotence."""
        for value in FORMAL_TO_INFORMAL.values():
            assert value not in FORMAL_TO_INFORMAL, (
                f"register_shift would cascade: {value!r} is both a value and a key"
            )
