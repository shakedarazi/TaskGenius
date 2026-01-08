# TASKGEMIUS — AI Insights Facade: Weekly Summary Specification

## Purpose
Generate a stable, structured weekly summary report derived from validated task data.
The report must be channel-independent and reusable by:
- Web UI
- Chat-triggered summaries
- Scheduled Telegram delivery

## Time Window
- Default: last 7 days for completed activity
- Lookahead: next 7 days for upcoming deadlines

## Required Sections
The report must include:
1) Completed tasks (last 7 days)
2) Open high-priority tasks (priority enum-based)
3) Tasks due within the next 7 days
4) Overdue tasks (deadline passed and not DONE/CANCELED)

## Output Requirements
- Output must be structured and stable (schema-like)
- Optional narrative text is allowed only if derived strictly from the structured report
- No new facts may be introduced by the model
- No mutations occur during report generation

## On-Demand vs Scheduled
- On-demand generation via chat and scheduled weekly generation must reuse the same report generator
- Only the delivery channel changes (chat response vs Telegram message)
