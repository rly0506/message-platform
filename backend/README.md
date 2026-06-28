# Dossier Intelligence Workbench Backend

后端提供事件搜索、新闻采集、去重入库、本地规则分析、搜索任务状态和事件证据 API。

## Core Endpoints

- `POST /api/search/jobs`
- `GET /api/search/jobs/{job_id}`
- `POST /api/search/jobs/{job_id}/rerun`
- `GET /api/topics`
- `GET /api/topics/{topic_id}`
- `GET /api/topics/{topic_id}/articles`
- `GET /api/topics/{topic_id}/local-events`

## Run

```powershell
uvicorn app.api:app --app-dir backend --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

## Test

```powershell
venv\Scripts\python.exe -m pytest backend\tests -q
```

## Optional spaCy NER

本地分析可使用 spaCy 提升中英文人物、组织、地点抽取；未安装 spaCy 或模型时会自动回退到 jieba/规则启发式。

```powershell
venv\Scripts\python.exe -m pip install -r backend\requirements.txt
venv\Scripts\python.exe -m spacy download zh_core_web_sm
venv\Scripts\python.exe -m spacy download en_core_web_sm
```

加载验证：

```powershell
venv\Scripts\python.exe -c "import spacy; spacy.load('zh_core_web_sm'); spacy.load('en_core_web_sm'); print('spaCy models ok')"
```

## Optional LLM Layer

核心搜索与本地分析不依赖 LLM。需要启用 LLM 富化/综合时，在 `backend/.env` 中配置：

```env
ANTHROPIC_API_KEY=your_pixel_api_key
ANTHROPIC_BASE_URL=https://ai-pixel.online
LLM_PROVIDER=openai
HAIKU_MODEL=gpt-5.4-mini
SYNTH_MODEL=gpt-5.4
```

验证端点、密钥和模型：

```powershell
venv\Scripts\python.exe backend\cli.py llm-check
```

LLM 工作流：

```powershell
venv\Scripts\python.exe backend\cli.py enrich <topic_id>
venv\Scripts\python.exe backend\cli.py build <topic_id>
```

## Main Modules

- `app/api.py`：FastAPI route surface.
- `app/db.py`：SQLModel models and SQLite setup.
- `app/topic_ops.py`：topic creation, collection, persistence bridge.
- `app/collectors/`：RSS and GDELT collectors.
- `app/pipeline/prefilter.py`：dedup and relevance scoring.
- `app/pipeline/local_analyze.py`：local no-LLM event analysis.
- `app/schemas/`：typed API payload boundaries.
- `config/rule_config.json`：media/entity/stopword rules.

## Notes

- 默认只存标题、摘要、链接、来源和时间，不存全文。
- 当前搜索任务执行方式是 SQLite 状态记录 + 进程内线程，适合 MVP。
- 核心链路不依赖 LLM；LLM 模块可通过 Pixel API / OpenAI-compatible endpoint 作为增强层启用。
