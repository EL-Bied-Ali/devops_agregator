"""
Generate a local HTML viewer for filtered jobs with full descriptions.

Usage:
  python jobs_viewer.py
  python jobs_viewer.py --input data/adzuna_jobs_filtered_strict_enriched.csv
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import unicodedata
import webbrowser
from html import escape
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

import adzuna_fetch as af
import filter_impact as fi
from config import SUPPORTED_CH_FOCUS, SUPPORTED_MARKETS, get_output_paths, resolve_filter_mode


DEFAULT_INPUT = "data/adzuna_jobs_filtered_strict_enriched.csv"
DEFAULT_OUTPUT = "data/job_viewer.html"
MA_LOCATION_FOCUS_CLUSTERS = {
    "rabat": ["rabat", "sale", "salé", "technopolis", "skhirat", "temara", "témara"],
    "casablanca": ["casablanca", "mohammedia", "bouskoura", "nouaceur", "sidi maarouf", "sidi maârouf"],
    "tanger": ["tanger", "tangier", "tetouan", "tétouan"],
    "rabat_or_remote": ["rabat", "sale", "salé", "technopolis", "skhirat", "temara", "témara"],
}

def safe_read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()

def normalize_match_text(*values: str) -> str:
    raw = " ".join(str(v or "") for v in values if str(v or ""))
    folded = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    return " ".join(folded.lower().split())

def resolve_location_focus_terms(location_focus: str, market: str) -> list[str]:
    focus = normalize_match_text(location_focus)
    if not focus:
        return []
    if market == "ma" and focus in MA_LOCATION_FOCUS_CLUSTERS:
        return [normalize_match_text(token) for token in MA_LOCATION_FOCUS_CLUSTERS[focus]]
    return [focus]

def record_matches_location_focus(record: dict, location_focus: str, market: str) -> bool:
    terms = resolve_location_focus_terms(location_focus, market)
    if not terms:
        return True
    if market == "ma" and normalize_match_text(location_focus) == "rabat_or_remote" and bool(record.get("is_remote", False)):
        return True
    loc_norm = normalize_match_text(record.get("location", ""))
    return any(term in loc_norm for term in terms)

def location_focus_path(path: str, location_focus: str) -> str:
    focus = normalize_match_text(location_focus)
    if not focus:
        return path
    safe_focus = focus.replace(" ", "_")
    p = Path(path)
    return str(p.with_name(f"{p.stem}_{safe_focus}{p.suffix}"))


def build_records(df: pd.DataFrame) -> list[dict]:
    existing_columns = set(df.columns)
    wanted = [
        "title",
        "company",
        "location",
        "created",
        "search_term",
        "priority_score",
        "junior_score",
        "language_fit_score",
        "is_remote",
        "keep_after_recheck",
        "apply_ready_after_recheck",
        "keep_before_recheck",
        "keep_after_full_recheck",
        "hard_excluded_after_recheck",
        "manual_review_after_recheck",
        "manual_review_reason",
        "fail_reason_after_recheck",
        "blocked_reason_detail",
        "seniority_flag",
        "years_required",
        "internship_flag",
        "work_mode",
        "why",
        "fetched_full_description",
        "combined_len",
        "url",
        "canonical_url",
        "source_url",
        "source_canonical_url",
        "fetch_used_url",
        "working_url",
        "combined_description",
        "description",
    ]
    for col in wanted:
        if col not in df.columns:
            df[col] = ""

    has_recheck_columns = any(
        col in existing_columns
        for col in [
            "apply_ready_after_recheck",
            "manual_review_after_recheck",
            "hard_excluded_after_recheck",
            "keep_before_recheck",
            "keep_after_full_recheck",
            "keep_after_recheck",
        ]
    )

    def as_text(v) -> str:
        if pd.isna(v):
            return ""
        return str(v)

    def as_int(v, default=0):
        if pd.isna(v):
            return default
        try:
            if str(v).strip() == "":
                return default
            return int(float(v))
        except Exception:
            return default

    records = []
    for _, row in df.iterrows():
        combined = as_text(row.get("combined_description", "")).strip()
        preview = as_text(row.get("description", "")).strip()
        desc = combined if combined else preview
        if has_recheck_columns:
            keep_after_recheck = str(row.get("keep_after_recheck", "")).strip().lower() in ("1", "true", "yes")
            hard_excluded = str(row.get("hard_excluded_after_recheck", "")).strip().lower() in ("1", "true", "yes")
            manual_review = str(row.get("manual_review_after_recheck", "")).strip().lower() in ("1", "true", "yes")
            apply_ready = str(row.get("apply_ready_after_recheck", "")).strip().lower() in ("1", "true", "yes")
            keep_before_recheck = str(row.get("keep_before_recheck", "")).strip().lower() in ("1", "true", "yes")
            keep_after_full_recheck = str(row.get("keep_after_full_recheck", "")).strip().lower() in ("1", "true", "yes")
            if not apply_ready:
                apply_ready = bool(keep_after_recheck and not hard_excluded and not manual_review)
        else:
            # Plain strict/broad CSV without recheck columns: treat visible rows as already usable.
            keep_before_recheck = True
            keep_after_full_recheck = True
            keep_after_recheck = True
            hard_excluded = False
            manual_review = False
            apply_ready = True

        records.append(
            {
                "title": as_text(row.get("title", "")),
                "company": as_text(row.get("company", "")),
                "location": as_text(row.get("location", "")),
                "created": as_text(row.get("created", "")),
                "search_term": as_text(row.get("search_term", "")),
                "priority_score": as_int(row.get("priority_score", 0), default=0),
                "junior_score": as_int(row.get("junior_score", 0), default=0),
                "language_fit_score": as_int(row.get("language_fit_score", 0), default=0),
                "sponsorship_score": as_int(row.get("sponsorship_score", 0), default=0),
                "hiring_likelihood_score": as_int(row.get("hiring_likelihood_score", 0), default=0),
                "is_remote": str(row.get("is_remote", "")).strip().lower() in ("1", "true", "yes"),
                "keep_after_recheck": keep_after_recheck,
                "apply_ready_after_recheck": apply_ready,
                "keep_before_recheck": keep_before_recheck,
                "keep_after_full_recheck": keep_after_full_recheck,
                "hard_excluded_after_recheck": hard_excluded,
                "manual_review_after_recheck": manual_review,
                "manual_review_reason": as_text(row.get("manual_review_reason", "")),
                "fail_reason_after_recheck": as_text(row.get("fail_reason_after_recheck", "")),
                "blocked_reason_detail": as_text(row.get("blocked_reason_detail", "")),
                "seniority_flag": as_text(row.get("seniority_flag", "")).strip() or "none",
                "years_required": as_int(row.get("years_required", ""), default="")
                if str(row.get("years_required", "")).strip()
                else (af.extract_years_required(as_text(row.get("title", "")), desc) or ""),
                "internship_flag": as_text(row.get("internship_flag", "")).strip() or "none",
                "work_mode": (
                    as_text(row.get("work_mode", "")).strip().lower()
                    if as_text(row.get("work_mode", "")).strip().lower() in {"remote", "hybrid", "onsite", "unknown"}
                    else af.detect_work_mode(
                        as_text(row.get("title", "")),
                        desc,
                        as_text(row.get("location", "")),
                    )
                ),
                "why": as_text(row.get("why", "")),
                "fetched_full_description": str(row.get("fetched_full_description", "")).strip().lower()
                in ("1", "true", "yes"),
                "combined_len": as_int(row.get("combined_len", 0), default=0),
                "url": as_text(row.get("url", "")),
                "canonical_url": as_text(row.get("canonical_url", "")),
                "source_url": as_text(row.get("source_url", "")),
                "source_canonical_url": as_text(row.get("source_canonical_url", "")),
                "fetch_used_url": as_text(row.get("fetch_used_url", "")),
                "working_url": as_text(row.get("working_url", "")),
                "description": desc,
            }
        )
    return records


def compute_independent_filter_impact(records: list[dict], filter_mode: str) -> dict:
    """
    Count how many rows would be removed by each filter independently.
    No early-stop chaining here: each filter is evaluated on all rows.
    """
    mode = resolve_filter_mode(filter_mode, allow_both=False)
    min_junior_score = 0 if mode == "strict" else -1
    total = len(records)
    out = {
        "total_rows": total,
        "description_too_short": 0,
        "bad_title": 0,
        "too_old": 0,
        "location_blocked": 0,
        "role_not_relevant": 0,
        "internship_student_only": 0,
        "exclude_keyword": 0,
        "blocked_language_requirement": 0,
        "blocked_language_detected": 0,
        "junior_score_below_min": 0,
    }

    for r in records:
        title = str(r.get("title", "") or "")
        desc = str(r.get("description", "") or "")
        loc = str(r.get("location", "") or "")
        created = str(r.get("created", "") or "")
        full = f"{title} {desc}"

        if af.REQUIRE_DESCRIPTION and len(desc.strip()) < af.MIN_DESCRIPTION_CHARS:
            out["description_too_short"] += 1

        norm_title = af.normalize(title)
        if any(pat in norm_title for pat in af.BAD_TITLE_KEYWORDS):
            out["bad_title"] += 1

        if not af.is_recent(created, af.MAX_DAYS_OLD):
            out["too_old"] += 1

        if not af.location_ok(loc, title, desc):
            out["location_blocked"] += 1

        if not af.role_relevant(title, desc):
            out["role_not_relevant"] += 1

        if af.internship_student_only_detail(title, desc):
            out["internship_student_only"] += 1

        hard_hits, _soft_hits = af.classify_excluded_hits(title, full)
        if hard_hits:
            out["exclude_keyword"] += 1

        if af.blocked_language_requirement_reason(full):
            out["blocked_language_requirement"] += 1
            out["blocked_language_detected"] += 1
        elif af.is_disallowed_language(full):
            out["blocked_language_detected"] += 1

        if af.compute_junior_score(title, desc) < min_junior_score:
            out["junior_score_below_min"] += 1

    return out


def compute_raw_to_strict_impact(raw_csv: str, filter_mode: str) -> dict:
    mode = resolve_filter_mode(filter_mode, allow_both=False)
    if not raw_csv or not os.path.exists(raw_csv):
        return {
            "available": False,
            "raw_csv": raw_csv,
            "steps": [],
            "final_after_dedup": 0,
            "what_if_skip": [],
            "analysis_trimmed": True,
        }

    raw_jobs = fi.load_raw_jobs(raw_csv)
    all_jobs = [fi.extract_fields(j) for j in raw_jobs]
    for idx, job in enumerate(all_jobs):
        job["row_id"] = idx

    steps = [
        ("description_length", lambda job: fi.check_description(job["description"])),
        ("bad_title", lambda job: fi.check_bad_title(job["title"])),
        ("recency", lambda job: fi.check_recency(job["created"])),
        ("location", lambda job: fi.check_location(job["location"], job["title"], job["description"])),
        ("role_relevant", lambda job: fi.check_role(job["title"], job["description"])),
        ("internship_student_only", lambda job: fi.check_internship_student_only(job["title"], job["description"])),
        ("exclude_keywords", lambda job: fi.check_excluded(job["title"], job["title"] + " " + job["description"])),
        (
            "blocked_language_requirement",
            lambda job: fi.check_blocked_language_requirement(job["title"] + " " + job["description"]),
        ),
        ("blocked_language", lambda job: fi.check_disallowed_language(job["title"] + " " + job["description"], mode)),
        ("junior_score", lambda job: fi.check_junior(job["title"], job["description"], mode)),
    ]

    current = list(all_jobs)
    step_rows = []
    for step_name, fn in steps:
        before = len(current)
        kept = []
        for job in current:
            result = fn(job)
            ok = bool(result[0])
            if ok:
                kept.append(job)
        removed = before - len(kept)
        pct = round((removed * 100.0 / before), 1) if before else 0.0
        step_rows.append({"step": step_name, "before": before, "removed": removed, "kept": len(kept), "pct_removed": pct})
        current = kept

    final_df = pd.DataFrame(current)
    if not final_df.empty:
        final_after_dedup = int(
            len(final_df.drop_duplicates(subset=["canonical_url", "title", "company"], keep="first"))
        )
    else:
        final_after_dedup = 0

    return {
        "available": True,
        "raw_csv": raw_csv,
        "raw_rows": len(all_jobs),
        "steps": step_rows,
        "final_after_dedup": final_after_dedup,
        "what_if_skip": [],
        "analysis_trimmed": True,
    }


def compute_strict_funnel(records: list[dict]) -> dict:
    total = len(records)
    strict_before = sum(1 for r in records if r.get("keep_before_recheck", False))
    passed_full = sum(1 for r in records if r.get("keep_after_full_recheck", False))
    hard_excluded = sum(1 for r in records if r.get("hard_excluded_after_recheck", False))
    manual_review = sum(1 for r in records if r.get("manual_review_after_recheck", False))
    apply_ready = sum(1 for r in records if r.get("apply_ready_after_recheck", False))
    blocked_after_full = max(0, strict_before - passed_full)

    reason_counts = {}
    for r in records:
        reason = str(r.get("fail_reason_after_recheck", "") or "").strip()
        if not reason:
            continue
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    return {
        "total_rows": total,
        "strict_before_recheck": strict_before,
        "blocked_after_full_recheck": blocked_after_full,
        "hard_excluded_after_recheck": hard_excluded,
        "manual_review_after_recheck": manual_review,
        "apply_ready_after_recheck": apply_ready,
        "top_fail_reasons": top_reasons,
    }


def build_html(
    records: list[dict],
    source_csv: str,
    filter_impact: dict,
    funnel: dict,
    raw_impact: dict,
    raw_rebuild_command: str,
) -> str:
    data_json = json.dumps(records, ensure_ascii=False)
    source_csv_json = json.dumps(source_csv, ensure_ascii=False)
    impact_json = json.dumps(filter_impact, ensure_ascii=False)
    funnel_json = json.dumps(funnel, ensure_ascii=False)
    raw_impact_json = json.dumps(raw_impact, ensure_ascii=False)
    raw_rebuild_command_json = json.dumps(raw_rebuild_command, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Job Viewer</title>
  <style>
    :root {{
      --bg: #f2f5f7;
      --ink: #102027;
      --muted: #4f636d;
      --card: #ffffff;
      --line: #d9e1e6;
      --accent: #005f73;
      --accent-soft: #e6f3f5;
      --ok: #0a7f44;
      --warn: #b45309;
      --bad: #b91c1c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 0% 0%, #e8f0f3, var(--bg));
    }}
    .wrap {{ max-width: 1200px; margin: 22px auto; padding: 0 14px 40px; }}
    .panel {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 14px;
      box-shadow: 0 6px 20px rgba(0,0,0,.04);
    }}
    h1 {{ margin: 0 0 6px; font-size: 22px; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    input, select {{
      width: 100%;
      padding: 8px 9px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
    }}
    .row {{
      display: flex;
      gap: 10px;
      align-items: center;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
      border: 1px solid transparent;
      margin-right: 6px;
      margin-top: 6px;
    }}
    .ok {{ color: var(--ok); background: #e9f8f0; border-color: #c8efd8; }}
    .warn {{ color: var(--warn); background: #fff7ea; border-color: #f3dfb5; }}
    .bad {{ color: var(--bad); background: #fdecec; border-color: #f6caca; }}
    .item h2 {{ margin: 0 0 4px; font-size: 19px; }}
    .sub {{ color: var(--muted); font-size: 13px; margin-bottom: 8px; }}
    .nums {{ font-family: Consolas, "Courier New", monospace; font-size: 12px; }}
    .desc {{
      margin-top: 10px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      white-space: pre-wrap;
      line-height: 1.35;
      font-size: 14px;
      max-height: 190px;
      overflow: auto;
    }}
    .links a {{ color: var(--accent); text-decoration: none; margin-right: 14px; font-size: 13px; }}
    .links a:hover {{ text-decoration: underline; }}
    .count {{
      font-weight: 600;
      color: var(--accent);
      background: var(--accent-soft);
      border: 1px solid #cce8ed;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 12px;
      display: inline-block;
      margin-top: 8px;
    }}
    .muted {{ color: var(--muted); }}
    .tiny {{ font-size: 12px; }}
    .impact-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}
    .impact-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: #fcfeff;
      font-size: 12px;
    }}
    .impact-card b {{ color: var(--accent); }}
    .btn {{
      padding: 7px 10px;
      border-radius: 8px;
      border: 1px solid #b9d7de;
      background: #ecf7fa;
      color: #094857;
      cursor: pointer;
      font-size: 12px;
    }}
    .btn:hover {{ background: #ddf0f5; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="panel">
      <h1>Jobs Viewer</h1>
      <div class="meta">Source: <code id="source"></code></div>
      <div class="grid">
        <div><input id="q" placeholder="Search title/company/location/description" /></div>
        <div>
          <select id="status">
            <option value="apply_plus_manual" selected>Apply-ready + manual review (recommended)</option>
            <option value="apply_ready">Apply ready only</option>
            <option value="manual">Show manual review only</option>
            <option value="excluded">Hard excluded</option>
            <option value="all">All statuses</option>
          </select>
        </div>
        <div>
          <select id="remote">
            <option value="all">Remote + onsite</option>
            <option value="remote">Remote only</option>
          </select>
        </div>
        <div><input id="minScore" type="number" min="0" step="1" value="0" placeholder="Min priority score" /></div>
        <div>
          <select id="sortBy">
            <option value="priority_desc">Sort: Priority high to low</option>
            <option value="created_desc">Sort: Most recent</option>
            <option value="company_asc">Sort: Company A-Z</option>
          </select>
        </div>
      </div>
      <div class="count" id="count"></div>
      <div class="tiny muted">Tip: If <code>combined_len</code> is around 400, description may still be preview-level.</div>
    </div>
    <div class="panel">
      <h1 style="font-size:18px">Strict Funnel (Sequential)</h1>
      <div class="tiny muted">Pipeline view from strict input to apply-ready.</div>
      <div class="impact-grid" id="funnel"></div>
      <div class="tiny muted" id="reasons"></div>
    </div>
    <div class="panel">
      <h1 style="font-size:18px">Raw -> Strict Impact (Sequential)</h1>
      <div class="tiny muted">From raw Adzuna search to strict final output.</div>
      <div class="impact-grid" id="rawflow"></div>
      <div class="tiny muted" id="rawwhatif"></div>
      <div class="row" style="margin-top:8px">
        <button id="rawRebuildBtn" class="btn" type="button">Rebuild raw impact (copy command)</button>
        <span class="tiny muted" id="rawCmdStatus"></span>
      </div>
      <div class="tiny muted" id="rawcmd"></div>
    </div>
    <div class="panel">
      <h1 style="font-size:18px">Filter Impact (Fair Count)</h1>
      <div class="tiny muted">Each filter is evaluated independently on all rows (no early-stop).</div>
      <div class="impact-grid" id="impact"></div>
    </div>
    <div id="list"></div>
  </div>
  <script>
    const DATA = {data_json};
    const SOURCE = {source_csv_json};
    const IMPACT = {impact_json};
    const FUNNEL = {funnel_json};
    const RAW_IMPACT = {raw_impact_json};
    const RAW_REBUILD_COMMAND = {raw_rebuild_command_json};
    document.getElementById("source").textContent = SOURCE;

    const qEl = document.getElementById("q");
    const statusEl = document.getElementById("status");
    const remoteEl = document.getElementById("remote");
    const minScoreEl = document.getElementById("minScore");
    const sortByEl = document.getElementById("sortBy");
    const listEl = document.getElementById("list");
    const countEl = document.getElementById("count");
    const impactEl = document.getElementById("impact");
    const funnelEl = document.getElementById("funnel");
    const reasonsEl = document.getElementById("reasons");
    const rawFlowEl = document.getElementById("rawflow");
    const rawWhatIfEl = document.getElementById("rawwhatif");
    const rawRebuildBtn = document.getElementById("rawRebuildBtn");
    const rawCmdStatusEl = document.getElementById("rawCmdStatus");
    const rawCmdEl = document.getElementById("rawcmd");

    function esc(s) {{
      return String(s || "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    }}

    function badge(label, cls) {{
      return `<span class="badge ${{cls}}">${{esc(label)}}</span>`;
    }}

    function includeByStatus(r, selected) {{
      if (selected === "all") return true;
      if (selected === "apply_plus_manual") return !!(r.apply_ready_after_recheck || r.manual_review_after_recheck);
      if (selected === "apply_ready") return !!r.apply_ready_after_recheck;
      if (selected === "keep") return !!r.keep_after_recheck;
      if (selected === "manual") return !!r.manual_review_after_recheck;
      if (selected === "excluded") return !!r.hard_excluded_after_recheck;
      return true;
    }}

    function includeBySearch(r, q) {{
      if (!q) return true;
      const blob = [
        r.title, r.company, r.location, r.search_term, r.manual_review_reason, r.blocked_reason_detail,
        r.seniority_flag, r.years_required, r.internship_flag, r.work_mode, r.why, r.description
      ].join(" ").toLowerCase();
      return blob.includes(q);
    }}

    function render() {{
      const q = qEl.value.trim().toLowerCase();
      const minScore = Number(minScoreEl.value || "0");
      const status = statusEl.value;
      const remote = remoteEl.value;
      const sortBy = sortByEl.value;

      let rows = DATA.filter(r =>
        includeByStatus(r, status) &&
        includeBySearch(r, q) &&
        r.priority_score >= minScore &&
        (remote === "all" || (remote === "remote" && r.is_remote))
      );

      if (sortBy === "priority_desc") {{
        rows.sort((a,b) => (b.priority_score - a.priority_score) || (b.sponsorship_score - a.sponsorship_score) || (b.hiring_likelihood_score - a.hiring_likelihood_score) || (b.junior_score - a.junior_score));
      }} else if (sortBy === "created_desc") {{
        rows.sort((a,b) => String(b.created).localeCompare(String(a.created)));
      }} else if (sortBy === "company_asc") {{
        rows.sort((a,b) => String(a.company).localeCompare(String(b.company)));
      }}

      countEl.textContent = `${{rows.length}} / ${{DATA.length}} jobs`;

      listEl.innerHTML = rows.map(r => {{
        const descLenWarning = r.combined_len > 0 && r.combined_len <= 420
          ? badge("possibly preview", "warn")
          : badge("long description", "ok");
        const recheck = r.hard_excluded_after_recheck
          ? badge("hard excluded", "bad")
          : (r.manual_review_after_recheck ? badge("manual review", "warn") : badge("apply ready", "ok"));
        const fetched = r.fetched_full_description ? badge("fetched", "ok") : badge("not fetched", "warn");
        const mode = (r.work_mode || "unknown");
        const remoteB = (mode === "remote" || mode === "hybrid")
          ? badge(`work mode: ${{mode}}`, "ok")
          : badge(`work mode: ${{mode}}`, "warn");
        const reason = r.manual_review_reason
          ? `<div class="sub"><b>Review reason:</b> ${{esc(r.manual_review_reason)}}</div>`
          : (r.fail_reason_after_recheck ? `<div class="sub"><b>Recheck reason:</b> ${{esc(r.fail_reason_after_recheck)}}</div>` : "");
        const reasonDetail = r.blocked_reason_detail
          ? `<div class="sub"><b>Blocked detail:</b> ${{esc(r.blocked_reason_detail)}}</div>`
          : "";
        const why = `<div class="sub"><b>Why:</b> ${{esc(r.why || "[]")}}</div>`;
        const years = (r.years_required === "" || r.years_required === null || r.years_required === undefined) ? "n/a" : String(r.years_required);
        const flags = `<div class="sub"><b>Flags:</b> seniority=${{esc(r.seniority_flag || "none")}} | years_required=${{esc(years)}} | internship=${{esc(r.internship_flag || "none")}} | work_mode=${{esc(mode)}}</div>`;
        // Use source/public URLs first. working/fetch URLs are for diagnostics/scraping.
        const link = r.source_url || r.url || r.source_canonical_url || r.canonical_url || r.working_url || r.fetch_used_url || "";
        return `
          <div class="panel item">
            <h2>${{esc(r.title)}} </h2>
            <div class="sub">${{esc(r.company)}} | ${{esc(r.location)}} | ${{esc(r.created)}}</div>
            <div>${{recheck}} ${{fetched}} ${{descLenWarning}} ${{remoteB}}</div>
            <div class="nums">priority=${{r.priority_score}} | sponsor=${{r.sponsorship_score}} | hire=${{r.hiring_likelihood_score}} | junior=${{r.junior_score}} | lang_fit=${{r.language_fit_score}} | combined_len=${{r.combined_len}} | term=${{esc(r.search_term)}}</div>
            ${{flags}}
            ${{why}}
            ${{reason}}
            ${{reasonDetail}}
            <div class="links">${{link ? `<a href="${{esc(link)}}" target="_blank" rel="noopener">open job page</a>` : ""}}</div>
            <div class="desc">${{esc(r.description)}}</div>
          </div>
        `;
      }}).join("");
    }}

    function renderImpact() {{
      const total = Number(IMPACT.total_rows || 0);
      const rows = [
        ["description too short", IMPACT.description_too_short || 0],
        ["bad title", IMPACT.bad_title || 0],
        ["too old", IMPACT.too_old || 0],
        ["location blocked", IMPACT.location_blocked || 0],
        ["role not relevant", IMPACT.role_not_relevant || 0],
        ["internship student only", IMPACT.internship_student_only || 0],
        ["exclude keyword", IMPACT.exclude_keyword || 0],
        ["blocked language req", IMPACT.blocked_language_requirement || 0],
        ["blocked language detected", IMPACT.blocked_language_detected || 0],
        ["junior score below min", IMPACT.junior_score_below_min || 0],
      ];
      impactEl.innerHTML = rows.map(([label, count]) => {{
        const pct = total > 0 ? ((count * 100.0) / total).toFixed(1) : "0.0";
        return `<div class="impact-card"><div>${{esc(label)}}</div><div><b>${{count}}</b> jobs (${{pct}}%)</div></div>`;
      }}).join("");
    }}

    function renderFunnel() {{
      const total = Number(FUNNEL.total_rows || 0);
      const rows = [
        ["rows in file", FUNNEL.total_rows || 0],
        ["strict before recheck", FUNNEL.strict_before_recheck || 0],
        ["blocked after full recheck", FUNNEL.blocked_after_full_recheck || 0],
        ["hard excluded", FUNNEL.hard_excluded_after_recheck || 0],
        ["manual review", FUNNEL.manual_review_after_recheck || 0],
        ["apply ready", FUNNEL.apply_ready_after_recheck || 0],
      ];
      funnelEl.innerHTML = rows.map(([label, count]) => {{
        const pct = total > 0 ? ((count * 100.0) / total).toFixed(1) : "0.0";
        return `<div class="impact-card"><div>${{esc(label)}}</div><div><b>${{count}}</b> jobs (${{pct}}%)</div></div>`;
      }}).join("");
      const top = Array.isArray(FUNNEL.top_fail_reasons) ? FUNNEL.top_fail_reasons : [];
      reasonsEl.textContent = top.length
        ? ("Top blocked reasons: " + top.map(x => `${{x[0]}}:${{x[1]}}`).join(", "))
        : "Top blocked reasons: none";
    }}

    function renderRawImpact() {{
      if (!RAW_IMPACT || !RAW_IMPACT.available) {{
        const reason = RAW_IMPACT && RAW_IMPACT.skipped
          ? "Raw impact skipped (fast mode)."
          : "Raw impact unavailable (raw CSV missing).";
        rawFlowEl.innerHTML = `<div class="impact-card">${{esc(reason)}}</div>`;
        rawWhatIfEl.textContent = "";
        return;
      }}
      const steps = Array.isArray(RAW_IMPACT.steps) ? RAW_IMPACT.steps : [];
      rawFlowEl.innerHTML = steps.map(s => {{
        return `<div class="impact-card"><div>${{esc(s.step)}}</div><div>before=<b>${{s.before}}</b> removed=<b>${{s.removed}}</b> (${{s.pct_removed}}%) kept=<b>${{s.kept}}</b></div></div>`;
      }}).join("");

      const whatIf = Array.isArray(RAW_IMPACT.what_if_skip) ? RAW_IMPACT.what_if_skip : [];
      const top = whatIf.filter(x => Number(x.delta_vs_strict || 0) > 0).slice(0, 5);
      const notes = [];
      if (RAW_IMPACT.analysis_trimmed) {{
        notes.push("What-if/detailed breakdown removed (non-essential for daily triage).");
      }} else {{
        notes.push(
          top.length
            ? ("What-if (skip one filter) top gains: " + top.map(x => `${{x.step}}:+${{x.delta_vs_strict}}`).join(", "))
            : "What-if (skip one filter): no positive gain"
        );
      }}
      if (RAW_IMPACT.detail_report_path) {{
        const href = esc(RAW_IMPACT.detail_report_path);
        notes.push(`<a href="${{href}}" target="_blank" rel="noopener">Open detailed stats page</a>`);
      }}
      rawWhatIfEl.innerHTML = notes.join(" | ");
    }}

    function setupRawCommandButton() {{
      if (!RAW_REBUILD_COMMAND) {{
        rawRebuildBtn.disabled = true;
        rawCmdStatusEl.textContent = "No command available.";
        return;
      }}
      rawCmdEl.textContent = `Command: ${{RAW_REBUILD_COMMAND}}`;
      rawRebuildBtn.addEventListener("click", async () => {{
        try {{
          if (navigator.clipboard && navigator.clipboard.writeText) {{
            await navigator.clipboard.writeText(RAW_REBUILD_COMMAND);
            rawCmdStatusEl.textContent = "Command copied. Run it in terminal.";
          }} else {{
            rawCmdStatusEl.textContent = "Clipboard unavailable. Copy the command below.";
          }}
        }} catch (_e) {{
          rawCmdStatusEl.textContent = "Copy failed. Copy the command below.";
        }}
      }});
    }}

    [qEl, statusEl, remoteEl, minScoreEl, sortByEl].forEach(el => {{
      el.addEventListener("input", render);
      el.addEventListener("change", render);
    }});
    renderFunnel();
    renderRawImpact();
    setupRawCommandButton();
    renderImpact();
    render();
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate a local HTML jobs viewer.")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input CSV path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output HTML path.")
    parser.add_argument(
        "--filter-mode",
        default="strict",
        choices=["strict", "broad"],
        help="Filter mode for independent impact counters.",
    )
    parser.add_argument(
        "--market",
        default="be",
        choices=SUPPORTED_MARKETS,
        help="Market profile used for location/language counters.",
    )
    parser.add_argument(
        "--ch-focus",
        default="all",
        choices=SUPPORTED_CH_FOCUS,
        help="CH focus used for location counters.",
    )
    parser.add_argument(
        "--raw-input",
        default="",
        help="Optional raw Adzuna CSV for raw->strict impact panel.",
    )
    parser.add_argument(
        "--raw-impact-mode",
        default="full",
        choices=["full", "skip"],
        help="Raw->strict impact computation mode. Use 'skip' for fast viewer refresh.",
    )
    parser.add_argument(
        "--location-focus",
        default="",
        help="Optional location cluster filter (e.g. rabat, casablanca, tanger).",
    )
    parser.add_argument("--no-open", action="store_true", help="Generate HTML only (do not open browser).")
    args = parser.parse_args()

    af.configure_market(args.market, args.ch_focus)
    df = safe_read_csv(args.input)
    if df.empty:
        raise SystemExit(f"[VIEWER] No data found in: {args.input}")

    records = build_records(df)
    if args.location_focus:
        before_focus = len(records)
        records = [r for r in records if record_matches_location_focus(r, args.location_focus, args.market)]
        print(
            f"[VIEWER] Location focus={args.location_focus} matched {len(records)}/{before_focus} rows "
            f"(market={args.market})"
        )
        if not records:
            raise SystemExit(f"[VIEWER] No records match location focus '{args.location_focus}'")
    impact = compute_independent_filter_impact(records, args.filter_mode)
    funnel = compute_strict_funnel(records)
    raw_key = "merged_raw_csv" if args.market == "ma" else "adzuna_raw_csv"
    default_raw = get_output_paths(args.market)[raw_key]
    raw_input_path = args.raw_input or default_raw
    if args.raw_impact_mode == "full":
        raw_impact = compute_raw_to_strict_impact(raw_input_path, args.filter_mode)
    else:
        # Fast path for post-enrichment refreshes: skip expensive raw->strict replay.
        raw_impact = {
            "available": False,
            "raw_csv": raw_input_path,
            "steps": [],
            "final_after_dedup": 0,
            "what_if_skip": [],
            "skipped": True,
            "analysis_trimmed": True,
        }
    output_path = location_focus_path(args.output, args.location_focus)
    out = Path(output_path)
    raw_impact["detail_report_path"] = ""

    rebuild_cmd = subprocess.list2cmdline(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--input",
            args.input,
            "--output",
            args.output,
            "--market",
            args.market,
            "--ch-focus",
            args.ch_focus,
            "--filter-mode",
            args.filter_mode,
            "--raw-input",
            raw_input_path,
            "--raw-impact-mode",
            "full",
            "--location-focus",
            args.location_focus,
            "--no-open",
        ]
    )
    html = build_html(records, args.input, impact, funnel, raw_impact, rebuild_cmd)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[VIEWER] HTML generated: {out}")
    print(f"[VIEWER] Rows loaded: {len(records)}")

    if not args.no_open:
        webbrowser.open(out.resolve().as_uri())
        print("[VIEWER] Opened in default browser.")


if __name__ == "__main__":
    main()

