"""Shared entry-building functions for plet runtime artifacts.

Internal module — imported by entries.py and util_cli.py, never called
directly. Not listed in allowed-tools. Not executable.

Provides canonical markdown templates for progress.md, learnings.md, and
emergent.md entries. Single source of truth for entry format — eliminates
drift between the entries CLI and invocation logging.

Functions:
    now_iso()
        Returns the current UTC time as ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ.

    build_progress_entry(plet_id, iteration, title, phase, attempt, status,
                         content_text)
        Build a progress.md entry string per formats.md RT_1.

    build_learning_entry(plet_id, iteration, title, category, entry_title,
                         content_text, phase)
        Build a learnings.md entry string per formats.md RT_2.

    build_emergent_entry(plet_id, em_number, iteration, title, entry_title,
                         phase, category, content_text)
        Build an emergent.md entry string per formats.md RT_3.

Dependencies: Python stdlib only (datetime).
"""

import datetime


def now_iso():
    """Return current UTC time as ISO 8601 string: YYYY-MM-DDTHH:MM:SSZ."""
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_progress_entry(plet_id, iteration, title, phase, attempt, status, content_text):
    """Build a progress.md entry string per formats.md RT_1."""
    # ENT_APR_BHV_8: suppress IN_PROGRESS from header
    if status == "IN_PROGRESS":
        header = f"### [{iteration}] {phase}-{attempt}"
    else:
        header = f"### [{iteration}] {phase}-{attempt} — {status}"

    lines = [
        f'<div id="plet-{plet_id}"></div>',
        "",
        "---",
        "",
        header,
        f"**PletId:** `{plet_id}`",
        f"**Timestamp:** {now_iso()}",
        f"**Iteration:** [{iteration}] {title}",
        f"**Phase:** {phase}",
        f"**Attempt:** {attempt}",
        "",
        "**Content:**",
        content_text,
        "",
        f'<div id="END-plet-{plet_id}"></div>',
        "",
    ]
    return "\n".join(lines)


def build_learning_entry(plet_id, iteration, title, category, entry_title, content_text, phase):
    """Build a learnings.md entry string per formats.md RT_2."""
    lines = [
        f'<div id="plet-{plet_id}"></div>',
        "",
        "---",
        "",
        f"### [{category}] {entry_title}",
        f"**PletId:** `{plet_id}`",
        f"**Timestamp:** {now_iso()}",
        f"**Iteration:** [{iteration}] {title}",
        f"**Phase:** {phase}",
        "",
        "**Content:**",
        content_text,
        "",
        f'<div id="END-plet-{plet_id}"></div>',
        "",
    ]
    return "\n".join(lines)


def build_emergent_entry(plet_id, em_ref, iteration, title, entry_title, phase, category, content_text):
    """Build an emergent.md entry string per formats.md RT_3."""
    lines = [
        f'<div id="plet-{plet_id}"></div>',
        "",
        "---",
        "",
        f"### {em_ref}: {entry_title}",
        f"**PletId:** `{plet_id}`",
        f"**Timestamp:** {now_iso()}",
        f"**Iteration:** [{iteration}] {title}",
        f"**Phase:** {phase}",
        f"**Category:** {category}",
        "**Outcome:** pending",
        "",
        "**Content:**",
        content_text,
        "",
        f'<div id="END-plet-{plet_id}"></div>',
        "",
    ]
    return "\n".join(lines)
