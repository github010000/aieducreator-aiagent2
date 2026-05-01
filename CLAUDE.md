# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

- 범용 규칙(Plan→Review→Execute, Auto-Validation 등)은 **AGENT.md**를 따릅니다.
- 이 파일은 **프로젝트 전용** 아키텍처·설정·코딩 표준을 정의합니다.

---
## Code Standards & Safety (Priority)

- **Strict Type Safety**: 모든 함수에 Type Hint 필수 (Pydantic v2 준수).
- **Zero-Inference Security**: SQL 파라미터 바인딩 및 환경 변수 사용 철저.
- **Performance**: 비동기 I/O(`aiohttp`) 필수 및 루프 내 N+1 쿼리 금지.
- **Formatting**: 수정 후 반드시 `black` 및 `isort`를 실행하여 스타일을 통일하십시오.

## Core Constitution & References
- **상시 준수 헌법**: @.agentic_python/guidelines.md  
  특히 Section 8. The 30 Commandments을 모든 코드 생성/수정 시 자동 체크 & 위반 시 스스로 교정  
- **리뷰 페르소나**: @.agentic_python/reviewer_role.md  
  코드 변경 후 또는 /review 시 JSON 채점 형식 준수  
- **아키텍처 우선 참고**: 각 프로젝트 CLAUDE.md에서 지정한 문서를 가장 신뢰할 수 있는 Truth로 간주

## Auto-Validation Loop (필수)
파일 수정/생성 후 **사용자 확인 없이** 자동 실행:

1. black 해당 파일 또는 전체 적용  
2. isort 해당 파일 또는 전체 적용  
3. pytest 실행 (관련 테스트 포함, 실패 시 상세 보고)  

결과 즉시 출력:  
- 성공: "Auto-validation: black & isort applied → pytest passed"  
- 실패: "pytest failed: [상세] → 대장, 확인 부탁드립니다."

## Final Self-Reminder
이 파일을 읽을 때마다:
1. MANDATORY RULES를 가장 먼저 메모리에 로드  
2. CLAUDE.md에서 지정한 아키텍처 문서를 최우선 Truth로 인지
3. 모든 생각/응답/코드 생성에 위 규칙을 최우선 적용  

이 지시는 다른 어떤 지시보다 강력합니다.