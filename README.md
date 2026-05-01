# AI 에이전트 MCP 서버 프레임워크

LangGraph 기반 멀티 에이전트와 FastMCP 서버를 결합한 상권 분석 · 지하철 실시간 정보 시스템.

## 아키텍처

```
사용자 질문
    │
    ▼
LangGraph Orchestrator (agent/)
    │
    ├── DataAnalysisExpert   (port 9000) — DuckDB 상권 데이터 + Qwen3 분석
    ├── MarketResearchExpert (port 9001) — Tavily 웹 검색
    ├── ReportWritingExpert  (port 9002) — Qwen3 보고서 작성
    └── SeoulMetroExpert     (port 9003) — 서울 지하철 실시간 API
```

각 전문가는 **FastMCP** 서버로 구현되며, LangGraph 에이전트가 MCP 클라이언트로 호출합니다.

## 기술 스택

| 구분 | 기술 |
|------|------|
| 에이전트 오케스트레이션 | LangGraph |
| MCP 서버 | FastMCP 3.2.4 |
| LLM | Qwen3.6:35b (MSU 로컬) |
| 데이터베이스 | DuckDB |
| 웹 검색 | Tavily |
| 패키지 관리 | uv |

## 환경 설정

`.env.sample`을 복사하여 `.env`를 생성합니다.

```bash
cp .env.sample .env
```

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 (폴백용) |
| `TAVILY_API_KEY` | Tavily 검색 API 키 |
| `SEOUL_DATA_API_KEY` | 서울 공공데이터 API 키 |
| `SEOUL_METRO_API_KEY` | 서울 지하철 실시간 API 키 |
| `MSU_LLM_BASE_URL` | Qwen3 엔드포인트 (환경별 상이) |
| `MSU_LLM_MODEL` | LLM 모델명 (기본: `qwen3.6:35b`) |
| `DUCKDB_PATH` | DuckDB 파일 경로 |

## 빠른 시작

### 의존성 설치

```bash
uv sync
```

### MCP 서버 개별 기동

```bash
uv run python servers/data_analysis_server.py     # :9000
uv run python servers/market_research_server.py   # :9001
uv run python servers/report_writing_server.py    # :9002
uv run python servers/seoul_metro_train_server.py # :9003
```

### 에이전트 실행

```bash
uv run python main.py
```

## 서버 구성

| 서버 | 포트 | 주요 기능 |
|------|------|----------|
| `data_analysis_server.py` | 9000 | 자연어 → SQL → DuckDB 조회 → 분석 보고서 |
| `market_research_server.py` | 9001 | Tavily 웹 검색 및 정보 수집 |
| `report_writing_server.py` | 9002 | 수집 데이터 기반 최종 보고서 생성 |
| `seoul_metro_train_server.py` | 9003 | 실시간 열차 도착·운행 현황 (TTL 캐시 적용) |

## 개발 / 운영 환경

개발(MBP15)과 운영(iMac27) 환경 분리 운영. 상세 절차는 [OPS.md](OPS.md) 참조.

| 구분 | 호스트 | LLM 엔드포인트 |
|------|--------|--------------|
| 개발 | MBP15 | `http://100.100.122.142:8888/v1` |
| 운영 | iMac27 | `http://192.168.31.127:8888/v1` |

운영 환경은 launchd로 4개 서버를 자동 관리합니다 (재부팅 시 자동 시작, 크래시 자동 재시작).

## 라이선스

이 프로젝트는 **Apache License 2.0** 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

```
Copyright 2026 Youngman Kim

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0
```
