"""Dossier CLI —— 专题情报追踪 (Phase 1: 采集 + 初筛 + 存储)。

用法示例:
  python cli.py add "新能源电池产业链" -q "新能源 电池 产业链" -q "lithium battery supply chain"
  python cli.py topics
  python cli.py collect 1 --gnews --gdelt --years 2
  python cli.py articles 1
"""
import errno
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# 让 `import app.*` 在从任意目录运行 cli.py 时都可用
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows 控制台默认 GBK，强制 UTF-8 输出，避免中文/符号编码崩溃
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from sqlmodel import Session, select

from app.db import (Analysis, Article, SourceFraming, TimelineEvent, Topic,
                    TopicArticle, engine, init_db)
from app import config, llm, topic_ops
from app.topic_seeds import TOPIC_SEEDS

app = typer.Typer(add_completion=False, help="个人专题情报追踪工具")


HEALTH_URL = "http://127.0.0.1:8000/api/health"
REFRESH_URL = "http://127.0.0.1:8000/api/auto-refresh/run"
HEALTH_TIMEOUT_SECONDS = 2
REFRESH_TIMEOUT_SECONDS = 30
AUTO_REFRESH_RESPONSE_KEYS = {
    "enabled",
    "running",
    "last_started_at",
    "last_finished_at",
    "last_error",
    "news_refreshed",
    "news_errors",
    "frontier_refreshed",
    "skipped_active",
}


@app.command("llm-check")
def llm_check(
    model: str = typer.Option("", help="覆盖测试模型；默认使用 HAIKU_MODEL"),
):
    """检查 LLM API key、base URL 和模型调用是否可用。"""
    target_model = model or config.HAIKU_MODEL
    typer.echo(f"LLM provider: {config.LLM_PROVIDER or '(auto)'}")
    typer.echo(f"LLM base URL: {config.LLM_BASE_URL or '(official provider default)'}")
    typer.echo(f"LLM model: {target_model}")
    try:
        text = llm.chat(
            target_model,
            "请只回复 ok 两个字母。",
            max_tokens=16,
            system="你是健康检查助手，只输出 ok。",
        )
    except Exception as exc:
        typer.echo(f"✗ LLM 调用失败: {type(exc).__name__}: {exc}")
        raise typer.Exit(1)
    typer.echo(f"✓ LLM 调用成功: {text.strip()[:80]}")


@app.command("discover")
def discover(
    annotate: bool = typer.Option(False, "--annotate", help="对种子做 LLM 二级分拣 (无 LLM 自动降级)"),
    print_report: bool = typer.Option(True, "--print/--no-print", help="是否打印报告到终端"),
):
    """事件发现: 拉注意力前沿 (HN/arXiv/智库) -> 存快照 -> 出认知前沿日报。

    每天跑一次, 攒快照基线; 次日起报告才有'加速'信号。
    报告同时落盘到 backend/discovery_reports/ (含结构化种子 sidecar)。
    """
    from app.discovery.run import run_and_save
    result = run_and_save(annotate=annotate)
    if print_report:
        typer.echo(result["markdown"])
    typer.echo(f"\n[报告已保存] {result['path']}  (种子 {len(result['seeds'])} 条)")


@app.command("daily-email")
def daily_email_cmd(
    preview: bool = typer.Option(False, "--preview", help="只打印邮件正文，不调用 Agent Mail"),
    send: bool = typer.Option(False, "--send", help="调用 Agent Mail 发起两阶段发送"),
    send_smtp: bool = typer.Option(False, "--send-smtp", help="使用 SMTP 直接发送，适合 Windows 任务计划"),
    to: str = typer.Option("", "--to", help="收件人；也可用 DAILY_DIGEST_TO 环境变量"),
    confirmation_token: str = typer.Option("", "--confirmation-token", help="Agent Mail 二阶段确认 token"),
):
    """把最新认知前沿日报整理成手机早报邮件。"""
    from app.discovery import daily_email as daily_email_mod
    from app.discovery import run as discovery_run
    from app.services import daily_briefing as daily_briefing_service

    report = discovery_run.latest_report()
    if report is None:
        typer.echo("还没有认知前沿日报；请先运行 `python backend/cli.py discover --no-print`。")
        raise typer.Exit(1)

    try:
        init_db()
        with Session(engine) as session:
            briefing = daily_briefing_service.build_daily_briefing(
                session,
                app_base_url=os.getenv(daily_briefing_service.APP_BASE_URL_ENV, ""),
            )
        report = {**report, "briefing": briefing}
    except Exception as exc:
        report = {
            **report,
            "briefing": None,
            "briefing_error": type(exc).__name__,
        }
        typer.echo("事实早报暂不可用，继续发送已归档的发现日报。", err=True)

    if preview or not (send or send_smtp):
        typer.echo(daily_email_mod.build_daily_digest_body(report))
        if not (send or send_smtp):
            typer.echo("\n[preview only] 加 --send 调用 Agent Mail，或加 --send-smtp 用于任务计划自动发送。")
        return

    recipient = to.strip() or daily_email_mod.recipient_from_env()
    if send_smtp:
        try:
            result = daily_email_mod.send_daily_digest_smtp(report, to=recipient)
        except daily_email_mod.DailyEmailError as exc:
            typer.echo(str(exc))
            raise typer.Exit(1)
        typer.echo(result.stdout.rstrip())
        return

    try:
        result = daily_email_mod.send_daily_digest(
            report,
            to=recipient,
            confirmation_token=confirmation_token,
        )
    except daily_email_mod.DailyEmailError as exc:
        typer.echo(str(exc))
        raise typer.Exit(1)

    if result.stdout:
        typer.echo(result.stdout.rstrip())
    if result.stderr:
        typer.echo(result.stderr.rstrip(), err=True)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
    if not confirmation_token:
        typer.echo("\n[Agent Mail] 如果上方返回 confirmation token，请确认无误后再次运行本命令并附加 --confirmation-token。")


@app.command()
def add(
    name: str,
    query: list[str] = typer.Option([], "--query", "-q", help="检索词/短语 (可多次, 支持多语种)"),
    desc: str = typer.Option("", "--desc", "-d", help="主题描述"),
):
    """新建一个追踪主题。"""
    init_db()
    queries = query or [name]
    with Session(engine) as s:
        t = Topic(name=name, description=desc, queries=queries)
        s.add(t)
        s.commit()
        s.refresh(t)
        typer.echo(f"✓ 已创建主题 #{t.id}: {t.name}")
        typer.echo(f"  检索词: {queries}")


@app.command()
def topics():
    """列出所有主题。"""
    init_db()
    with Session(engine) as s:
        rows = s.exec(select(Topic)).all()
        if not rows:
            typer.echo("(还没有主题，用 `add` 创建)")
            return
        for t in rows:
            n = len(s.exec(select(TopicArticle).where(TopicArticle.topic_id == t.id)).all())
            typer.echo(f"#{t.id}  {t.name}  [{t.status}]  文章 {n} 篇")
            typer.echo(f"     检索词: {t.queries}")


@app.command("init-seeds")
def init_seeds():
    """Create broad long-running news topics from the built-in seed library."""
    init_db()
    created = 0
    skipped = 0
    with Session(engine) as s:
        existing = {t.name for t in s.exec(select(Topic)).all()}
        for seed in TOPIC_SEEDS:
            if seed["name"] in existing:
                skipped += 1
                continue
            s.add(Topic(
                name=seed["name"],
                description=seed["description"],
                queries=seed["queries"],
            ))
            created += 1
        s.commit()
    typer.echo(f"seed topics created={created}, skipped={skipped}")


@app.command("update-all")
def update_all(
    gnews: bool = typer.Option(True, help="Use Google News RSS."),
    gdelt_on: bool = typer.Option(False, "--gdelt/--no-gdelt", help="Use GDELT backfill."),
    years: int = typer.Option(1, help="GDELT backfill years."),
    min_rel: float = typer.Option(0.0, help="Minimum keyword relevance."),
    limit_topics: int = typer.Option(0, help="Only update the first N topics; 0 means all."),
):
    """Collect every active topic, then rebuild no-LLM major-event timelines."""
    init_db()
    with Session(engine) as s:
        rows = s.exec(select(Topic).where(Topic.status == "active")).all()
        if limit_topics > 0:
            rows = rows[:limit_topics]
        if not rows:
            typer.echo("No active topics. Run `python backend/cli.py init-seeds` first.")
            return
        for topic in rows:
            typer.echo(f"\n== update #{topic.id}: {topic.name} ==")
            stats = topic_ops.collect_topic(s, topic, gnews, gdelt_on, years, [], min_rel)
            typer.echo(
                f"collect: raw={stats['raw']} kept={stats['kept']} "
                f"new_articles={stats['new_articles']} new_links={stats['new_links']}"
            )
            data = topic_ops.analyze_topic(s, topic, persist=True)
            typer.echo(
                f"local timeline: events={len(data.get('events', []))} "
                f"framing={len(data.get('framing', []))} articles={data.get('article_count', 0)}"
            )


@app.command("build-local-all")
def build_local_all():
    """Rebuild no-LLM timelines for all active topics using existing articles."""
    init_db()
    with Session(engine) as s:
        rows = s.exec(select(Topic).where(Topic.status == "active")).all()
        for topic in rows:
            data = topic_ops.analyze_topic(s, topic, persist=True)
            typer.echo(
                f"#{topic.id} {topic.name}: events={len(data.get('events', []))} "
                f"framing={len(data.get('framing', []))} articles={data.get('article_count', 0)}"
            )


@app.command()
def collect(
    topic_id: int,
    gnews: bool = typer.Option(True, help="Google News RSS 多语种增量"),
    gdelt_on: bool = typer.Option(False, "--gdelt/--no-gdelt", help="GDELT 历史回填"),
    years: int = typer.Option(1, help="GDELT 回填年数"),
    feed: list[str] = typer.Option([], "--feed", help="额外的显式 RSS feed URL (可多次)"),
    curated: bool = typer.Option(False, "--curated", help="并入精选通讯社/大报/周刊 RSS 源"),
    min_rel: float = typer.Option(0.0, help="最低相关性阈值, 低于则丢弃"),
):
    """围绕主题采集 + 初筛 + 入库。"""
    init_db()
    with Session(engine) as s:
        topic = s.get(Topic, topic_id)
        if not topic:
            typer.echo(f"✗ 找不到主题 #{topic_id}")
            raise typer.Exit(1)

        typer.echo(f"采集主题 #{topic.id}: {topic.name}")
        stats = topic_ops.collect_topic(
            s,
            topic,
            gnews,
            gdelt_on,
            years,
            feed,
            min_rel,
            use_curated_feeds=curated,
        )
        typer.echo(
            f"✓ 完成: 原始 {stats['raw']} 条, 保留 {stats['kept']} 条, "
            f"新增文章 {stats['new_articles']} 篇, 新增关联 {stats['new_links']} 条"
        )


@app.command()
def articles(
    topic_id: int,
    limit: int = typer.Option(20, help="显示条数"),
):
    """查看某主题已采集的文章 (按发布时间倒序)。"""
    init_db()
    with Session(engine) as s:
        links = s.exec(select(TopicArticle).where(TopicArticle.topic_id == topic_id)).all()
        if not links:
            typer.echo("(该主题暂无文章)")
            return
        ids = [l.article_id for l in links]
        rel = {l.article_id: l.relevance for l in links}
        arts = s.exec(select(Article).where(Article.id.in_(ids))).all()
        arts.sort(key=lambda a: (a.published_at or datetime.min), reverse=True)
        typer.echo(f"主题 #{topic_id} 共 {len(arts)} 篇，显示前 {min(limit, len(arts))}:\n")
        for a in arts[:limit]:
            d = a.published_at.strftime("%Y-%m-%d") if a.published_at else "????-??-??"
            typer.echo(f"  [{d}] ({a.source_lang or '?'}|rel={rel.get(a.id, 0)}) {a.title}")
            typer.echo(f"        {a.source} · {a.collector} · {a.url}")


@app.command("enrich")
def enrich_cmd(
    topic_id: int,
    limit: int = typer.Option(40, help="本次最多富化多少篇 (省钱开关)"),
):
    """LLM 富化 (Haiku): 相关性确认 + 译中 + 单篇立场。"""
    init_db()
    with Session(engine) as s:
        topic = s.get(Topic, topic_id)
        if not topic:
            typer.echo(f"✗ 找不到主题 #{topic_id}"); raise typer.Exit(1)

        typer.echo(f"富化主题 #{topic_id}: {topic.name}")
        stats = topic_ops.enrich_topic_articles(s, topic, limit=limit)
        if not stats["pending"]:
            typer.echo("没有待富化的文章 (都处理过了)"); return

        if stats["errors"]:
            for error in stats["errors"]:
                typer.echo(f"  {error}")
        typer.echo(
            f"✓ 富化完成: {stats['processed']} 篇/"
            f"{stats['pending']} 待处理，其中判定相关 {stats['relevant']} 篇"
        )


@app.command()
def build(
    topic_id: int,
    enrich_limit: int = typer.Option(0, help="先富化多少篇未处理报道；0 表示只综合已富化报道"),
):
    """LLM 综合 (Sonnet): 生成时间线 + 各方态度 + 批判分析。"""
    init_db()
    with Session(engine) as s:
        topic = s.get(Topic, topic_id)
        if not topic:
            typer.echo(f"✗ 找不到主题 #{topic_id}"); raise typer.Exit(1)

        typer.echo(f"深度分析主题 #{topic_id}: {topic.name}")
        result = topic_ops.run_deep_analysis(s, topic, enrich_limit=enrich_limit)
        typer.echo(
            f"✓ 完成: 富化 {result['enrich']['processed']} 篇/"
            f"{result['enrich']['pending']} 待处理，"
            f"时间线 {result['synthesize']['timeline']} 节点, "
            f"立场 {result['synthesize']['framing']} 方, 批判分析已生成"
        )
        typer.echo("  用 `show {}` 查看档案".format(topic_id))


@app.command("build-local")
def build_local(topic_id: int):
    """No-LLM synthesis: major event timeline + stance evolution."""
    init_db()
    with Session(engine) as s:
        topic = s.get(Topic, topic_id)
        if not topic:
            typer.echo(f"找不到主题 #{topic_id}")
            raise typer.Exit(1)

        data = topic_ops.analyze_topic(s, topic, persist=True)
        if not data.get("article_count"):
            typer.echo("该主题还没有可分析的文章，请先 collect。")
            raise typer.Exit(1)

        typer.echo(
            f"完成: 输入 {data.get('article_count', 0)} 篇报道，"
            f"重大事件 {len(data.get('events', []))} 个，"
            f"态度分组 {len(data.get('framing', []))} 个。"
        )
        typer.echo(f"用 `python backend/cli.py show {topic_id}` 查看结果。")


@app.command()
def show(topic_id: int):
    """展示专题档案 (时间线 / 各方态度 / 批判分析)。"""
    init_db()
    with Session(engine) as s:
        topic = s.get(Topic, topic_id)
        if not topic:
            typer.echo(f"✗ 找不到主题 #{topic_id}"); raise typer.Exit(1)
        typer.echo(f"\n{'='*60}\n📂 专题档案 #{topic.id}: {topic.name}\n{'='*60}")

        events = s.exec(select(TimelineEvent).where(TimelineEvent.topic_id == topic_id)).all()
        events.sort(key=lambda e: (e.date or datetime.min))
        typer.echo("\n🕐 时间线")
        for e in events:
            d = e.date.strftime("%Y-%m-%d") if e.date else "????-??-??"
            typer.echo(f"  [{d}] {e.title_zh}")
            if e.summary_zh:
                typer.echo(f"          {e.summary_zh}")

        framing = s.exec(select(SourceFraming).where(SourceFraming.topic_id == topic_id)).all()
        typer.echo("\n🗣️  各方态度")
        for f in framing:
            typer.echo(f"  • {f.party} [{f.stance}]: {f.summary_zh}")

        analysis = s.exec(select(Analysis).where(Analysis.topic_id == topic_id)).all()
        if analysis:
            typer.echo("\n🔍 批判分析\n")
            typer.echo(analysis[-1].content_md)
        typer.echo("")


@app.command("remove-topic")
def remove_topic(
    topic_ids: list[int] = typer.Argument(..., help="要删除的主题 id (可多个)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="确认执行删除 (否则仅预览)"),
):
    """按 id 级联删除主题及其关联表 (timeline/framing/analysis/关联)。

    默认仅预览要删除的内容；加 --yes 才真正删除。
    仅删除"该主题独占"的文章；被其他主题共享的文章会保留。
    """
    init_db()
    with Session(engine) as s:
        for tid in topic_ids:
            result = topic_ops.remove_topic(s, tid, dry_run=not yes)
            if not result["found"]:
                typer.echo(f"✗ 找不到主题 #{tid}，跳过")
                continue

            typer.echo(
                f"#{tid} {result['topic_name']!r}: 关联 {result['links']}、"
                f"独占文章 {result['exclusive_articles']}、时间线 {result['timeline']}、"
                f"立场 {result['framing']}、分析 {result['analysis']}"
            )
            if not yes:
                typer.echo("  (预览模式，未删除；加 --yes 执行)")
                continue

            typer.echo(f"  ✓ 已删除主题 #{tid} 及其关联数据")


def _parse_date(s: str):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return None


@app.command("coverage-status")
def coverage_status(
    start: str = typer.Option(..., "--start"),
    end: str = typer.Option(..., "--end"),
    root: str = typer.Option("", "--root"),
):
    """Summarize verified evidence without SQLite access or a source decision."""
    from app.services import coverage_observation

    start_date, end_date = _coverage_dates(start, end)
    observations_root = Path(root) if root else Path(config.COVERAGE_OBSERVATIONS_DIR)
    verification = coverage_observation.verify_observations(
        root=observations_root, start_date=date.min, end_date=date.max
    )
    if not verification["valid"]:
        typer.echo(json.dumps(verification, ensure_ascii=False, sort_keys=True))
        raise typer.Exit(1)
    typer.echo(json.dumps(
        _coverage_status_payload(verification, observations_root, start_date, end_date),
        ensure_ascii=False,
        sort_keys=True,
    ))


@app.command("coverage-verify")
def coverage_verify(
    start: str = typer.Option(..., "--start"),
    end: str = typer.Option(..., "--end"),
    root: str = typer.Option("", "--root"),
):
    """Validate immutable evidence from the filesystem only."""
    from app.services import coverage_observation

    start_date, end_date = _coverage_dates(start, end)
    observations_root = Path(root) if root else Path(config.COVERAGE_OBSERVATIONS_DIR)
    verification = coverage_observation.verify_observations(
        root=observations_root, start_date=start_date, end_date=end_date
    )
    typer.echo(json.dumps(verification, ensure_ascii=False, sort_keys=True))
    if not verification["valid"]:
        raise typer.Exit(1)


def _coverage_dates(start: str, end: str) -> tuple[date, date]:
    try:
        start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        _command_error("--start and --end must be ISO dates")
        raise AssertionError("unreachable")
    if end_date < start_date:
        _command_error("--end must not precede --start")
    return start_date, end_date


def _coverage_status_payload(
    verification: dict[str, object], root: Path, requested_start: date, requested_end: date
) -> dict[str, object]:
    valid_runs = verification["runs"]
    assert isinstance(valid_runs, list)
    complete_runs = [
        run for run in valid_runs
        if isinstance(run, dict)
        and bool(run["manifest"]["captured"])
        and not run["manifest"]["observation_failed"]
    ]
    successful_dates = sorted({str(run["date"]) for run in complete_runs})
    first_success = date.fromisoformat(successful_dates[0]) if successful_dates else None
    window_end = first_success + timedelta(days=13) if first_success else None
    in_window = [
        item for item in successful_dates
        if first_success is not None and date.fromisoformat(item) <= window_end
    ]
    representatives: dict[tuple[str, int], dict[str, object]] = {}
    for run in complete_runs:
        manifest = run["manifest"]
        assert isinstance(manifest, dict)
        if window_end is not None and date.fromisoformat(str(run["date"])) > window_end:
            continue
        for topic_id in manifest["captured"]:
            key = (str(run["date"]), int(topic_id))
            previous = representatives.get(key)
            if previous is None or str(manifest["captured_at_utc"]) > str(previous["manifest"]["captured_at_utc"]):
                representatives[key] = run
    topic_dates: dict[int, set[str]] = {}
    for observed_date, topic_id in representatives:
        if first_success is not None and date.fromisoformat(observed_date) <= window_end:
            topic_dates.setdefault(topic_id, set()).add(observed_date)
    recurring_topics = sum(1 for dates in topic_dates.values() if len(dates) >= 3)
    collector_degraded = 0
    fulltext_metadata_debt = 0
    unclassified_metadata_debt = 0
    for (observed_date, topic_id), run in representatives.items():
        manifest = run["manifest"]
        assert isinstance(manifest, dict)
        run_dir = root / str(run["date"]) / str(run["run_id"])
        entry = next(entry for entry in manifest["topic_files"] if entry["topic_id"] == topic_id)
        payload = json.loads((run_dir / entry["path"]).read_text(encoding="utf-8"))
        if payload.get("collection_result", {}).get("errors"):
            collector_degraded += 1
        if payload.get("coverage_snapshot", {}).get("fulltext", {}).get("status") != "available":
            fulltext_metadata_debt += 1
        unclassified_metadata_debt += len(
            payload.get("coverage_snapshot", {}).get("source_registry", {}).get("unclassified_article_ids", [])
        )
    review_earliest = max(date(2026, 7, 27), first_success + timedelta(days=13)) if first_success else None
    evidence_sufficient = len(in_window) >= 10 and recurring_topics >= 3
    return {
        "first_successful_date": first_success.isoformat() if first_success else None,
        "window_end": window_end.isoformat() if window_end else None,
        "review_earliest": review_earliest.isoformat() if review_earliest else None,
        "successful_dates": in_window,
        "successful_date_count": len(in_window),
        "topics_with_three_dates": recurring_topics,
        "topic_distinct_shanghai_dates": {str(topic_id): sorted(dates) for topic_id, dates in sorted(topic_dates.items())},
        "collector_degraded_observations": collector_degraded,
        "fulltext_metadata_debt": fulltext_metadata_debt,
        "unclassified_metadata_debt": unclassified_metadata_debt,
        "review_state": "HUMAN_REVIEW_REQUIRED" if evidence_sufficient else "HOLD",
        "requested_start": requested_start.isoformat(),
        "requested_end": requested_end.isoformat(),
    }


@app.command("refresh-once")
def refresh_once():
    """Run one refresh through the live backend, or one refused-only offline call."""
    try:
        health = _request_json(HEALTH_URL, timeout=HEALTH_TIMEOUT_SECONDS)
    except (ConnectionRefusedError, URLError) as exc:
        if _is_connection_refused(exc):
            _run_local_refresh_once()
            return
        _command_error(f"health transport failed: {type(exc).__name__}")
    except (HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        _command_error(f"health check failed: {type(exc).__name__}")

    if health[0] != 200 or not isinstance(health[1], dict) or health[1].get("status") != "ok":
        _command_error("health response was not the expected 200 {status: ok}")

    try:
        status, result = _request_json(
            Request(REFRESH_URL, data=b"", method="POST"),
            timeout=REFRESH_TIMEOUT_SECONDS,
        )
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        _command_error(f"refresh request failed: {type(exc).__name__}")

    if status != 200 or not _is_valid_auto_refresh_result(result):
        _command_error("refresh response did not match the auto-refresh contract")
    typer.echo(json.dumps(result, ensure_ascii=False, sort_keys=True))


def _request_json(request: str | Request, *, timeout: int) -> tuple[int, object]:
    with urlopen(request, timeout=timeout) as response:
        return int(response.status), json.loads(response.read().decode("utf-8"))


def _is_connection_refused(exc: BaseException) -> bool:
    reason = exc.reason if isinstance(exc, URLError) else exc
    return isinstance(reason, ConnectionRefusedError) or (
        isinstance(reason, OSError) and reason.errno in {errno.ECONNREFUSED, 10061}
    )


def _is_valid_auto_refresh_result(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != AUTO_REFRESH_RESPONSE_KEYS:
        return False
    timestamps = (value["last_started_at"], value["last_finished_at"])
    return (
        isinstance(value["enabled"], bool)
        and isinstance(value["running"], bool)
        and all(timestamp is None or isinstance(timestamp, str) for timestamp in timestamps)
        and isinstance(value["last_error"], str)
        and isinstance(value["news_refreshed"], int)
        and not isinstance(value["news_refreshed"], bool)
        and isinstance(value["news_errors"], list)
        and all(isinstance(item, str) for item in value["news_errors"])
        and isinstance(value["frontier_refreshed"], bool)
        and isinstance(value["skipped_active"], int)
        and not isinstance(value["skipped_active"], bool)
    )


def _run_local_refresh_once() -> None:
    from app.services import auto_refresh

    init_db()
    typer.echo(json.dumps(auto_refresh.refresh_once(), ensure_ascii=False, sort_keys=True))


def _command_error(message: str) -> None:
    typer.echo(json.dumps({"error": message}, ensure_ascii=False, sort_keys=True))
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
