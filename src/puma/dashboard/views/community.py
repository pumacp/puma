"""Community view: graphical 4-state wizard around ``puma share-results``.

States, in order:

* :data:`STATE_AUTH` — GitHub token not configured; instructions + refresh.
* :data:`STATE_BROWSE` — list shareable runs and let the user pick one.
* :data:`STATE_CONSENT` — preview the constructed submission payload and
  choose between local dry-run save or real publish.
* :data:`STATE_PUBLISH` — execute the chosen action and surface the result.

The view composes the same modules ``puma share-results`` uses on the CLI;
no subprocess shell-outs.
"""

from __future__ import annotations

import json
import logging
import secrets
from typing import Any, cast

import streamlit as st

from puma.community.builder import (
    CommunityError,
    ExcludedModelError,
    PIIDetectedError,
    UnknownScenarioError,
    UnknownStrategyError,
    build_submission_from_run,
)
from puma.community.credentials import CredentialStore
from puma.community.dry_run_saver import save_dry_run
from puma.community.github_client import (
    APIRateLimitError,
    AuthenticationError,
    CommunityGitHubClient,
    ConflictError,
    GitHubError,
)
from puma.community.ratelimit import LocalRateLimiter
from puma.community.runs_query import get_run_summary, list_shareable_runs
from puma.community.schema import Submitter
from puma.community.validator import is_safe_to_publish
from puma.storage.db import session_scope

logger = logging.getLogger("puma.dashboard.community")

STATE_AUTH = "auth"
STATE_BROWSE = "browse"
STATE_CONSENT = "consent"
STATE_PUBLISH = "publish"

_SESSION_KEY = "community"


# ── session state ────────────────────────────────────────────────────────────


def _init_session_state() -> None:
    if _SESSION_KEY not in st.session_state:
        st.session_state[_SESSION_KEY] = {
            "state": STATE_BROWSE,
            "selected_run_id": None,
            "last_result": None,
            "action_mode": None,
            "allow_dry_run_without_token": False,
        }


def _community_state() -> dict[str, Any]:
    return cast(dict[str, Any], st.session_state[_SESSION_KEY])


def _has_github_token() -> bool:
    try:
        return CredentialStore().get("github") is not None
    except Exception as exc:
        logger.debug("credential store read failed: %s", exc)
        return False


def _resolve_state() -> str:
    state = str(_community_state()["state"])
    if (
        state in (STATE_BROWSE, STATE_CONSENT)
        and not _has_github_token()
        and not _community_state()["allow_dry_run_without_token"]
    ):
        return STATE_AUTH
    return state


def _transition_to(new_state: str) -> None:
    _community_state()["state"] = new_state


def _reset_wizard() -> None:
    st.session_state[_SESSION_KEY] = {
        "state": STATE_BROWSE,
        "selected_run_id": None,
        "last_result": None,
        "action_mode": None,
        "allow_dry_run_without_token": _community_state().get(
            "allow_dry_run_without_token", False
        ),
    }


# ── auth state ───────────────────────────────────────────────────────────────


def _render_auth() -> None:
    st.warning("GitHub token not configured.")
    st.markdown(
        "Run `puma auth login github` in a terminal to store a Personal Access "
        "Token, then click **Refresh** below. Alternatively, you can proceed in "
        "dry-run mode without a token: nothing is uploaded; the submission "
        "payload is saved locally for review."
    )
    cols = st.columns(2)
    if cols[0].button("🔄 Refresh", key="community_auth_refresh"):
        st.rerun()
    if cols[1].button("Continue in dry-run mode", key="community_auth_dry"):
        _community_state()["allow_dry_run_without_token"] = True
        _transition_to(STATE_BROWSE)
        st.rerun()


# ── browse state ─────────────────────────────────────────────────────────────


@st.cache_data(ttl=30, show_spinner=False)
def _cached_shareable_runs() -> list[dict[str, Any]]:
    return [
        {
            "run_id": s.run_id,
            "scenario": s.scenario,
            "model": s.model,
            "strategy": s.strategy,
            "n_predictions": s.n_predictions,
            "started_at": s.started_at,
        }
        for s in list_shareable_runs()
    ]


def _render_browse() -> None:
    st.subheader("Pick a shareable run")
    try:
        rows = _cached_shareable_runs()
    except Exception as exc:
        logger.warning("could not list shareable runs: %s", exc)
        st.error(f"Could not read runs from the local database: {exc}")
        return

    if not rows:
        st.info("No shareable runs found. Run `puma run <spec.yaml>` first to generate results.")
        return

    st.dataframe(rows, use_container_width=True, hide_index=True)
    run_id_input = st.text_input(
        "Paste a run_id to share",
        key="community_browse_input",
        help="Copy a run_id from the table above and paste it here.",
    )
    if run_id_input:
        summary = get_run_summary(run_id_input.strip())
        if summary is None:
            st.error(f"Run {run_id_input!r} not found, or its status is not 'done'.")
            return
        _community_state()["selected_run_id"] = summary.run_id
        _transition_to(STATE_CONSENT)
        st.rerun()


# ── consent state ────────────────────────────────────────────────────────────


def _resolve_alias() -> str:
    return f"anonymous-{secrets.token_hex(4)}"


def _build_submitter(alias: str) -> Submitter:
    return Submitter(
        name_or_alias=alias,
        affiliation=None,
        contact=None,
        consent_public_release=True,
        consent_redistribution=True,
        consent_research_use=True,
    )


def _build_payload(run_id: str, alias: str) -> dict[str, Any] | None:
    try:
        with session_scope() as session:
            submission = build_submission_from_run(
                run_id=run_id,
                submitter=_build_submitter(alias),
                session=session,
            )
    except (
        UnknownScenarioError,
        UnknownStrategyError,
        ExcludedModelError,
        PIIDetectedError,
        CommunityError,
    ) as exc:
        st.error(f"Cannot build submission: {exc}")
        return None
    payload = cast(dict[str, Any], json.loads(submission.model_dump_json()))
    safe, reasons = is_safe_to_publish(submission)
    if not safe:
        st.error("Submission failed safety checks:")
        for reason in reasons:
            st.markdown(f"- {reason}")
        return None
    return payload


def _render_consent() -> None:
    state = _community_state()
    run_id = state["selected_run_id"]
    if not run_id:
        _transition_to(STATE_BROWSE)
        st.rerun()
        return

    alias = _resolve_alias()
    payload = _build_payload(run_id, alias)
    if payload is None:
        if st.button("← Back to browse", key="community_consent_back_err"):
            _transition_to(STATE_BROWSE)
            st.rerun()
        return

    rm = payload["run_metadata"]
    metrics = payload["metrics"]
    sustainability = payload["sustainability"]
    integrity = payload["integrity"]

    st.subheader(f"Review submission for `{run_id}`")
    cols = st.columns(3)
    cols[0].markdown(f"**Scenario**\n\n`{rm['scenario']}`")
    cols[1].markdown(f"**Model**\n\n`{rm['model']}`")
    cols[2].markdown(f"**Strategy**\n\n`{rm['strategy']}`")
    st.caption(f"Submitter alias: `{alias}` · {rm['n_instances']} instances")

    st.markdown("**Metrics**")
    metric_cols = st.columns(3)
    if metrics.get("f1_macro") is not None:
        metric_cols[0].metric("F1 macro", f"{metrics['f1_macro']:.4f}")
    if metrics.get("mae") is not None:
        metric_cols[1].metric("MAE", f"{metrics['mae']:.2f}")
    if metrics.get("ece") is not None:
        metric_cols[2].metric("ECE", f"{metrics['ece']:.4f}")
    if metrics.get("accuracy") is not None:
        metric_cols[0].metric("Accuracy", f"{metrics['accuracy']:.4f}")

    st.markdown("**Sustainability**")
    sus_cols = st.columns(2)
    sus_cols[0].metric("CO₂ (g)", f"{sustainability['co2_grams_total']:.2f}")
    sus_cols[1].metric("Energy (kWh)", f"{sustainability['energy_kwh_total']:.4f}")

    st.markdown(
        f"**Integrity hash:** `{integrity['predictions_summary_hash'][:12]}…`"
    )

    state["_pending_payload"] = payload
    state["_pending_alias"] = alias

    has_token = _has_github_token()
    btn_cols = st.columns(2)
    if btn_cols[0].button(
        "📦 Save locally (dry-run)",
        key="community_consent_dry",
        use_container_width=True,
    ):
        state["action_mode"] = "dry-run"
        _transition_to(STATE_PUBLISH)
        st.rerun()
    publish_disabled = not has_token
    publish_tooltip = (
        "Run `puma auth login github` to enable publishing." if publish_disabled else None
    )
    if btn_cols[1].button(
        "🚀 Publish to PUMA Community",
        key="community_consent_publish",
        disabled=publish_disabled,
        help=publish_tooltip,
        use_container_width=True,
    ):
        state["action_mode"] = "publish"
        _transition_to(STATE_PUBLISH)
        st.rerun()

    if st.button("← Back to browse", key="community_consent_back_ok"):
        _transition_to(STATE_BROWSE)
        st.rerun()


# ── publish state ────────────────────────────────────────────────────────────


def _do_dry_run(payload: dict[str, Any]) -> dict[str, Any]:
    path = save_dry_run(payload=payload)
    return {"ok": True, "kind": "dry-run", "path": str(path)}


def _do_publish(payload: dict[str, Any], alias: str) -> dict[str, Any]:
    limiter = LocalRateLimiter()
    ok, reason = limiter.can_submit(submitter_alias=alias)
    if not ok:
        return {"ok": False, "kind": "publish", "error": reason}
    try:
        client = CommunityGitHubClient()
    except AuthenticationError as exc:
        return {"ok": False, "kind": "publish", "error": str(exc)}

    submission_id = payload["submission_id"]
    rm = payload["run_metadata"]
    try:
        fork_owner = client.ensure_fork()
        branch = client.create_submission_branch(
            fork_owner=fork_owner, submission_id=submission_id
        )
        client.write_submission_file(
            fork_owner=fork_owner,
            branch=branch,
            submission_id=submission_id,
            payload_json=json.dumps(payload, indent=2, sort_keys=True),
            commit_message=f"data(community): add submission {submission_id}",
        )
        title = (
            f"Submission {submission_id[:12]}: "
            f"{rm['scenario']} / {rm['model']} / {rm['strategy']}"
        )
        body = (
            f"Submission generated via the PUMA Dashboard Community view.\n\n"
            f"- Scenario: `{rm['scenario']}`\n"
            f"- Model: `{rm['model']}`\n"
            f"- Strategy: `{rm['strategy']}`\n"
            f"- predictions_summary_hash: `{payload['integrity']['predictions_summary_hash']}`\n"
        )
        result = client.open_pull_request(
            fork_owner=fork_owner,
            branch=branch,
            submission_id=submission_id,
            title=title,
            body=body,
        )
    except APIRateLimitError as exc:
        return {"ok": False, "kind": "publish", "error": f"Rate limit: {exc}"}
    except ConflictError as exc:
        return {"ok": False, "kind": "publish", "error": f"Conflict: {exc}"}
    except GitHubError as exc:
        return {"ok": False, "kind": "publish", "error": f"GitHub error: {exc}"}

    limiter.record_submission(submitter_alias=alias, submission_id=submission_id)
    return {
        "ok": True,
        "kind": "publish",
        "pr_url": result.pr_url,
        "pr_number": result.pr_number,
    }


def _render_publish() -> None:
    state = _community_state()
    payload = state.get("_pending_payload")
    alias = state.get("_pending_alias")
    action = state.get("action_mode")
    last_result = state.get("last_result")

    if last_result is None:
        if payload is None or action is None:
            st.warning("Nothing to publish. Going back to browse.")
            _transition_to(STATE_BROWSE)
            st.rerun()
            return
        with st.spinner("Working…"):
            if action == "dry-run":
                last_result = _do_dry_run(payload)
            else:
                last_result = _do_publish(payload, alias or "anonymous")
        state["last_result"] = last_result
        state["_pending_payload"] = None
        state["_pending_alias"] = None

    if last_result.get("ok"):
        if last_result["kind"] == "dry-run":
            st.success(f"Saved dry-run submission to:\n\n`{last_result['path']}`")
        else:
            st.success(
                f"Pull request opened: [#{last_result['pr_number']}]({last_result['pr_url']})"
            )
    else:
        st.error(last_result.get("error", "Action failed."))

    if st.button("🔄 Share another run", key="community_publish_again"):
        _reset_wizard()
        st.rerun()


# ── entry point ──────────────────────────────────────────────────────────────


def render() -> None:
    """Main entry point invoked by the dashboard router."""
    st.title("🤝 PUMA Community")
    st.caption("Share local-LLM benchmark results with the PUMA Community")

    _init_session_state()
    state = _resolve_state()

    if state == STATE_AUTH:
        _render_auth()
    elif state == STATE_BROWSE:
        _render_browse()
    elif state == STATE_CONSENT:
        _render_consent()
    elif state == STATE_PUBLISH:
        _render_publish()
    else:  # pragma: no cover — guarded by the constants
        logger.warning("unknown community wizard state %r — resetting", state)
        _reset_wizard()
        st.rerun()


__all__ = [
    "STATE_AUTH",
    "STATE_BROWSE",
    "STATE_CONSENT",
    "STATE_PUBLISH",
    "render",
]
