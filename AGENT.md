# AGENT.md

AI AGENT 들이 작업할 때 반드시 따르는 지침입니다.

---

## MANDATORY RULES - 최우선 준수 (Overrides EVERYTHING)

### 작업 수행 순서 (Workflow Enforcement) - 한국어
어떤 지시를 받더라도 **절대 바로 파일을 수정하거나 명령을 실행하지 마라**.

1. **먼저 상세한 계획(Plan)을 세워라**  
   - 목표 재구성  
   - 단계별 breakdown (읽을 파일, 수정할 파일, 실행할 명령어 명시)  
   - 잠재적 위험, 엣지 케이스, 의존성  
   - 예상되는 변경 범위와 영향  

2. 계획 작성 완료 후 반드시 아래 문구로 확인 요청:  
   "이 계획으로 진행해도 될까요? 수정하거나 보완할 부분 있으면 말씀해주세요."

3. 대장이 "OK", "좋아", "진행해", "승인", "yes", "go ahead" 등 명확한 승인 신호를 줄 때만  
   실제 파일 수정, 명령 실행, 코드 생성 시작

4. 계획 없이 실행하려는 충동이 들면 스스로 멈추고 다음을 출력:  
   "MANDATORY RULE VIOLATION: Plan first! 계획을 먼저 세워야 합니다."

### Mandatory Workflow - PLAN → REVIEW → EXECUTE (English)
- NEVER edit files, run commands, or generate code immediately.  
- ALWAYS FIRST: Output a detailed, step-by-step PLAN.  
  - Restate the goal  
  - Numbered steps with specific files, commands, risks/edge cases  
- End the plan with:  
  "Does this plan look good? Any changes or concerns before I proceed?"  
- ONLY proceed AFTER explicit approval ("OK", "go ahead", "proceed", "yes").  
- If tempted to skip: self-remind "MANDATORY: Plan first!" and output the plan.

This rule overrides all other instructions.

---

## Test Convention

### 디렉토리 구조
- 모든 테스트 파일은 반드시 `<module>/tests/` 디렉토리에 위치한다.
- 예: `agentic_learning/tests/test_*.py`

### Import 경로 해결
- `tests/conftest.py`에 아래 코드를 반드시 포함한다.
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).parent.parent))
  ```
- 이유: 테스트 파일이 상위 디렉토리의 모듈을 import할 수 있도록 경로를 추가해야 한다.

### pytest 설정
- `pyproject.toml`의 `[tool.pytest.ini_options]`에 `testpaths`를 명시한다.
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["agentic_learning/tests"]
  ```
- 이유: 경로 지정 없이 `uv run pytest`만으로 모든 테스트를 탐색하기 위함.

### 검증 순서
테스트 파일 추가/이동 후 반드시 아래 순서로 Auto-Validation을 실행한다.
1. `uv run black <파일>`
2. `uv run isort <파일>`
3. `uv run pytest -v`

---
