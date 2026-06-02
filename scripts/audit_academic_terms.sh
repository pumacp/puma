#!/usr/bin/env bash
#
# audit_academic_terms.sh — reproducible detection of academic-context content
# in the PUBLIC-FACING documentation of the pumacp/puma repository.
#
# Part of Sprint 12 Epic E3 (US-12.9). DETECTION ONLY — this script never
# modifies any file. It scans a fixed in-scope file set for seven pattern
# categories and prints structured, tab-separated matches for triage.
#
# Re-run in future Sprints as a regression check on academic-content drift.
#
# Scope (searched):
#   README.md, CONTRIBUTING.md, CHANGELOG.md, LICENSE (if present),
#   docs/ (full tree), wiki/ (if present), .github/ (free-text + workflow
#   names), src/ (broadly — human triage decides which matches are
#   user-facing strings vs internal).
# Out of scope (NOT searched):
#   tests/ (fixtures), commit history, companion repos, Anexos .docx, and
#   docs/internal/ (gitignored: not part of the published repo). rg honours
#   .gitignore, so docs/internal/ is skipped automatically; an explicit
#   exclude is added belt-and-suspenders.
#
# Pattern categories (name | intent | default classification):
#   academic-identity          TFG/UOC/Núria/PEC/memoria/tribunal/Anexo/…  REEMPLAZAR
#   legacy-naming              AgentPM                                     REEMPLAZAR
#   non-existent-method        "MIT Student Method"                        REEMPLAZAR
#   forbidden-term-HELM        HELM (must be zero; any hit is CRITICAL)    CRITICAL
#   forbidden-term-federation  Federación/federation/federated            DUDOSO
#   citation-non-registered    "<Surname> et al." outside the approved      DUDOSO
#                              registry {Strubell, Guo, Kitchenham, Cohen}
#   sprint-internal-language   Sprint N / S12.x / D2x / PAUSE / FASE        DUDOSO
#
# Searches are case-insensitive (a superset of case-sensitive) so nothing is
# missed; the report triage refines each default classification.
#
# Output: one tab-separated line per match:
#   FILE <TAB> LINE <TAB> MATCH_TEXT(<=100 chars) <TAB> CATEGORY <TAB> CLASS
# Sectioned by "===== CATEGORY =====" headers, ending with a SUMMARY line.

set -uo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

RG="$(command -v rg || true)"
if [ -z "$RG" ]; then
    echo "ERROR: ripgrep (rg) is required but was not found in PATH" >&2
    exit 2
fi

# In-scope paths — only those that actually exist on disk.
CANDIDATES=(README.md CONTRIBUTING.md CHANGELOG.md LICENSE docs wiki .github src)
SCOPE=()
for p in "${CANDIDATES[@]}"; do
    [ -e "$p" ] && SCOPE+=("$p")
done

# Common rg flags: case-insensitive, PCRE2 (lookahead + \b), line numbers,
# include hidden files (needed for .github), no colour. .gitignore is honoured
# (skips docs/internal/, data/, results/, …); explicit excludes reinforce it.
RG_COMMON=(-i -P --no-heading --line-number --with-filename --color never --hidden
    -g '!.git/**' -g '!docs/internal/**' -g '!**/__pycache__/**' -g '!**/*.pyc'
    # Exclude this audit's own report: it quotes every match verbatim, so
    # leaving it in scope would make the detector recursively match itself.
    -g '!docs/sprints/Sprint-12-Academic-Audit.md')

TOTAL=0
CATEGORIES_WITH_HITS=0

run_category() {
    local name="$1" regex="$2" cls="$3"
    echo "===== ${name} ====="
    local out
    out="$("$RG" "${RG_COMMON[@]}" -e "$regex" "${SCOPE[@]}" 2>/dev/null |
        awk -F: -v cat="$name" -v cls="$cls" 'BEGIN { OFS = "\t" }
            {
                file = $1
                line = $2
                text = substr($0, length($1) + length($2) + 3)
                gsub(/\t/, " ", text)
                if (length(text) > 100) text = substr(text, 1, 100)
                print file, line, text, cat, cls
            }' |
        { iconv -c -f UTF-8 -t UTF-8 2>/dev/null || cat; })"
    # iconv -c drops any invalid byte left by truncating a match excerpt mid
    # multibyte char, so the report appendix stays valid UTF-8; falls back to
    # cat if iconv is unavailable.
    if [ -z "$out" ]; then
        echo "(no matches)"
    else
        echo "$out"
        local n
        n="$(printf '%s\n' "$out" | wc -l | tr -d ' ')"
        TOTAL=$((TOTAL + n))
        CATEGORIES_WITH_HITS=$((CATEGORIES_WITH_HITS + 1))
    fi
    echo ""
}

run_category "academic-identity" \
    '\bTFG\b|Trabajo (Final de Grado|de Fin de Grado|Fin de Grado)|Final Degree Project|\bUOC\b|Universitat Oberta|Universidad Abierta|N[uú]ria|75\.656|Aula 4|\bPEC[1-4]\b|\btribunal\b|memoria acad[eé]mica|\bmemoria\b|\bAnexo [A-Z]\b|\btesis\b|thesis defense|\bdefensa\b' \
    "REEMPLAZAR"

run_category "legacy-naming" \
    '\bAgentPM\b' \
    "REEMPLAZAR"

run_category "non-existent-method" \
    'MIT Student Method' \
    "REEMPLAZAR"

run_category "forbidden-term-HELM" \
    '\bHELM\b' \
    "CRITICAL"

run_category "forbidden-term-federation" \
    '\bFederaci[oó]n\b|\bfederation\b|\bfederated\b' \
    "DUDOSO"

run_category "citation-non-registered" \
    '\b(?!(?:Strubell|Guo|Kitchenham|Cohen)\b)[A-Za-z]{2,} et al\.?' \
    "DUDOSO"

run_category "sprint-internal-language" \
    "\\bSprint [0-9]+|\\bS1[0-9]\\.[0-9]|\\bD2[0-9]\\b|PAUSE [0-9]|\\bFASE [AB]\\b|S11'" \
    "DUDOSO"

FILES_SCANNED="$("$RG" --files "${RG_COMMON[@]}" "${SCOPE[@]}" 2>/dev/null | wc -l | tr -d ' ')"
echo "===== SUMMARY ====="
echo "${TOTAL} matches across ${CATEGORIES_WITH_HITS} categories, files scanned: ${FILES_SCANNED}"
