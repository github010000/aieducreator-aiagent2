# MCP 서버 운영 가이드

## 환경 구성

| 구분 | 호스트 | 역할 | LLM 엔드포인트 |
|------|--------|------|---------------|
| 개발 | MBP15 (`100.69.98.154`) | 코드 편집 · 로컬 테스트 | `http://100.100.122.142:8888/v1` |
| 운영 | iMac27 (`100.113.74.153`) | 서비스 상시 기동 | `http://192.168.31.127:8888/v1` |

### 서버 포트

| 서버 | 포트 | launchd 레이블 |
|------|------|----------------|
| DataAnalysisExpert | 9000 | `com.k010k.mcp.data-analysis` |
| MarketResearchExpert | 9001 | `com.k010k.mcp.market-research` |
| ReportWritingExpert | 9002 | `com.k010k.mcp.report-writing` |
| SeoulMetroExpert | 9003 | `com.k010k.mcp.seoul-metro` |

### 디렉터리 구조

```
MBP15 (개발)
└── ~/workspaces/study/aieducreator-aiagent2/
    ├── servers/          ← 소스 코드 (편집 위치)
    ├── .env              ← 개발 환경 설정
    └── OPS.md

iMac27 (운영)
└── ~/AI/mcps/
    ├── servers/          ← 배포된 서버 코드
    ├── data/
    │   └── sales.duckdb
    ├── logs/             ← 서버 로그 (*.log, *.err)
    └── .env              ← 운영 환경 설정
```

---

## 개발 절차

### 1. 로컬 서버 기동 (MBP15)

```bash
cd ~/workspaces/study/aieducreator-aiagent2
uv run python servers/data_analysis_server.py    # 9000
uv run python servers/market_research_server.py  # 9001
uv run python servers/report_writing_server.py   # 9002
uv run python servers/seoul_metro_train_server.py # 9003
```

### 2. 로컬 테스트

```bash
curl -s http://localhost:9000/mcp -X POST \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'
```

---

## 배포 절차 (MBP15 → iMac27)

### 전체 배포

```bash
rsync -av --exclude='__pycache__' \
  ~/workspaces/study/aieducreator-aiagent2/servers/ \
  k010k@100.113.74.153:~/AI/mcps/servers/
```

### 단일 파일 배포

```bash
rsync -av ~/workspaces/study/aieducreator-aiagent2/servers/<파일명>.py \
  k010k@100.113.74.153:~/AI/mcps/servers/<파일명>.py
```

### 배포 후 서비스 재시작

```bash
# 특정 서버만
ssh k010k@100.113.74.153 "
  launchctl unload ~/Library/LaunchAgents/com.k010k.mcp.data-analysis.plist
  launchctl load  ~/Library/LaunchAgents/com.k010k.mcp.data-analysis.plist
"

# 전체 재시작
ssh k010k@100.113.74.153 "
  for name in data-analysis market-research report-writing seoul-metro; do
    launchctl unload ~/Library/LaunchAgents/com.k010k.mcp.\${name}.plist
    launchctl load  ~/Library/LaunchAgents/com.k010k.mcp.\${name}.plist
  done
"
```

---

## 운영 관리 (iMac27)

### 서비스 상태 확인

```bash
ssh k010k@100.113.74.153 "
  for port in 9000 9001 9002 9003; do
    result=\$(curl -s --max-time 3 http://localhost:\${port}/mcp -X POST \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1\"}}}' \
      | grep -o '\"name\":\"[^\"]*\"' | head -1)
    echo \"port \${port}: \${result:-FAILED}\"
  done
"
```

### 로그 확인

```bash
# 실시간 로그
ssh k010k@100.113.74.153 "tail -f ~/AI/mcps/logs/data-analysis.log"

# 에러 로그
ssh k010k@100.113.74.153 "tail -50 ~/AI/mcps/logs/data-analysis.err"
```

### 서비스 수동 중지 / 시작

```bash
ssh k010k@100.113.74.153 "launchctl stop com.k010k.mcp.data-analysis"
ssh k010k@100.113.74.153 "launchctl start com.k010k.mcp.data-analysis"
```

---

## 환경 설정 파일 관리

### 개발 (.env — MBP15)

```
MSU_LLM_BASE_URL=http://100.100.122.142:8888/v1
MSU_LLM_MODEL=qwen3.6:35b
DUCKDB_PATH=<프로젝트 루트>/sales.duckdb
MCP_HOST=0.0.0.0
MCP_PORT=9000
MARKET_MCP_PORT=9001
REPORT_MCP_PORT=9002
METRO_MCP_PORT=9003
```

### 운영 (.env — iMac27 `~/AI/mcps/.env`)

```
MSU_LLM_BASE_URL=http://192.168.31.127:8888/v1
MSU_LLM_MODEL=qwen3.6:35b
DUCKDB_PATH=/Users/k010k/AI/mcps/data/sales.duckdb
MCP_HOST=0.0.0.0
MCP_PORT=9000
MARKET_MCP_PORT=9001
REPORT_MCP_PORT=9002
METRO_MCP_PORT=9003
```

> **주의**: `.env`는 Git에서 제외됨. API 키 변경 시 두 환경 모두 수동 업데이트 필요.

---

## 신규 서버 추가 시 체크리스트

1. `servers/<name>_server.py` 작성
   - `_folder` 기반 절대경로 `load_dotenv`
   - `MCP_HOST`, `MCP_PORT` 환경변수 읽기
   - `mcp_server.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT)`
2. `.env` (개발/운영 모두) 포트 변수 추가
3. iMac27 launchd plist 생성 및 등록
4. OpenClaw `mcporter.json`에 `host.docker.internal:<port>` 추가
5. `agent/config.py` `SERVER_REGISTRY`에 등록
