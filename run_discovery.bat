@echo off
REM 事件发现 - 每日认知前沿日报
REM 由 Windows 任务计划程序每天调用一次, 攒快照基线 + 出报告。
REM 报告落盘到 backend\discovery_reports\frontier-*.md

cd /d "%~dp0"
call venv\Scripts\python.exe backend\cli.py discover --no-print
