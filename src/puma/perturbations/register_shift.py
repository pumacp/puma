"""Register-shift perturbation: formal technical English → informal.

Substitutes formal technical phrases with their informal/colloquial
equivalents while preserving semantic meaning. Acts as a proxy for the
dialect/register-variation axis on technical corpora where natural
dialectal variation is absent.

The substitution table is intentionally conservative: each pair is a
semantically-stable rewrite that a human reader would accept as
synonymous in a bug-triage context. Values are chosen so they never
appear as keys of another rule (verified by `test_register_shift.py`),
which makes the operation idempotent.

Reference:
    Tatman, R. (2017). Gender and dialect bias in YouTube's automatic
    captions. In Proceedings of the First ACL Workshop on Ethics in
    Natural Language Processing.
"""

from __future__ import annotations

FORMAL_TO_INFORMAL: dict[str, str] = {
    "is experiencing": "is having",
    "has been observed": "we saw",
    "exhausted": "dying",
    "cannot establish": "can't make",
    "is unable to": "can't",
    "has encountered": "hit",
    "is failing": "is broken",
    "investigation required": "need to check",
    "production server": "prod box",
    "intermittently": "on and off",
    "immediate": "ASAP",
    "configuration": "config",
    "application": "app",
    "database": "DB",
    "request": "call",
    "response": "reply",
    "endpoint": "URL",
    "deployment": "rollout",
    "currently": "right now",
}


def apply(text: str, seed: int = 0) -> str:
    """Apply formal → informal substitutions in declaration order."""
    if not text:
        return text
    for formal, informal in FORMAL_TO_INFORMAL.items():
        text = text.replace(formal, informal)
    return text
