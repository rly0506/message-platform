# Dossier Intelligence Workbench Frontend

Vue 3 + TypeScript + Vite 前端，用于事件关键词搜索、搜索任务轮询、事件时间轴、来源矩阵、关键实体和原始报道分组展示。

## Run

```powershell
npm install
npm run dev
```

## Build

```powershell
npm run build
```

## E2E

```powershell
npm run test:e2e
```

## Main Files

- `src/App.vue`：event workbench page composition.
- `src/api/dossierApi.ts`：typed API client.
- `src/types/dossier.ts`：shared frontend DTOs.
- `src/style.css`：page styles.
- `tests/e2e/source-matrix.spec.ts`：Playwright coverage for source matrix and article grouping.
