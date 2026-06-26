# 상테크 & 리셀 실적 관리

Excel 없이 모바일 웹에서 상품권 재테크와 크림/솔드아웃 리셀 거래를 입력하고, 월별 수익과 마일리지 적립 현황을 관리하는 FastAPI 기반 SPA입니다. 데이터 기준 연도는 2026년부터입니다.

## 기술 스택

- Backend: Python, FastAPI, SQLAlchemy ORM, SQLite, Pydantic
- Frontend: HTML, Vanilla JavaScript, CSS
- 배포: Render.com Web Service + Persistent Disk

## 폴더 구조

```text
.
├── main.py
├── database.py
├── models.py
├── schemas.py
├── seed.py
├── routers/
│   ├── __init__.py
│   ├── dashboard.py
│   ├── santech.py
│   ├── cream.py
│   └── mileage.py
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── requirements.txt
├── render.yaml
└── README.md
```

## 로컬 실행

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Windows PowerShell에서 `pip` 명령을 찾지 못하면 아래처럼 실행합니다.

```powershell
.\install.cmd
.\run.cmd
```

PowerShell 스크립트 실행 정책을 허용한 환경에서는 아래 명령도 사용할 수 있습니다.

```powershell
.\install.ps1
.\run.ps1
```

또는 Python 경로를 직접 지정할 수 있습니다.

```powershell
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m pip install -r requirements.txt
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m uvicorn main:app --reload
```

접속 주소:

```text
http://localhost:8000
```

## DB 위치

앱은 시작 시 SQLite DB 경로를 자동 선택합니다.

- `/data` 디렉터리가 있으면 `/data/santech.db`
- 없으면 프로젝트 폴더의 `santech.db`

Render 배포에서는 `render.yaml`의 persistent disk가 `/data`에 마운트됩니다.

## Render 배포

1. Git 저장소를 Render에 연결합니다.
2. `render.yaml`을 사용해 Web Service를 생성합니다.
3. persistent disk가 `/data`에 연결되어 있는지 확인합니다.
4. 배포 후 앱은 `uvicorn main:app --host 0.0.0.0 --port $PORT`로 실행됩니다.

## GitHub Actions 배포

PC를 꺼도 휴대폰에서 접속하려면 GitHub Actions가 직접 서버를 계속 실행하는 방식이 아니라, Render Web Service에 배포해야 합니다.

무료로 오래 쓰려면 Render 무료 Web Service와 외부 무료 Postgres(Supabase 등)를 함께 사용하는 구성이 가장 안전합니다. Render 무료 Web Service는 15분 정도 요청이 없으면 잠들 수 있고, 다음 접속 때 1분 안팎으로 다시 깨어납니다. SQLite 파일 저장은 무료 Render 재시작/재배포 때 데이터가 사라질 수 있으므로, 폰에서 계속 관리할 용도라면 `DATABASE_URL`에 Postgres 연결 문자열을 넣어 사용하세요.

1. Render에서 이 GitHub 저장소를 연결하고 `render.yaml`로 Web Service를 생성합니다.
2. Supabase에서 무료 Postgres 프로젝트를 만들고 연결 문자열을 복사합니다.
3. Render 환경변수에 아래 값을 추가합니다.
   - `DATABASE_URL`: Supabase Postgres 연결 문자열
   - `SANTECH_DEFAULT_PASSWORD`: 기본 계정 비밀번호
   - `SANTECH_CRON_SECRET`: GitHub Actions가 일일 메일 발송 API를 호출할 때 쓸 임의의 긴 문자열
   - `RESEND_API_KEY`: Render 무료 플랜에서 메일 발송에 사용할 Resend API 키
   - `RESEND_FROM`: 발신자. 테스트는 `Santech Report <onboarding@resend.dev>`를 사용할 수 있습니다.
   - `SMTP_HOST`: 메일 SMTP 서버
   - `SMTP_PORT`: 보통 `587`
   - `SMTP_USERNAME`: SMTP 로그인 계정
   - `SMTP_PASSWORD`: SMTP 비밀번호 또는 앱 비밀번호
   - `SMTP_FROM`: 발신자 메일 주소
   - `SMTP_STARTTLS`: 보통 `true`
   - `SMTP_FORCE_IPV4`: Render에서 Gmail SMTP 연결이 막히는 경우를 피하기 위해 `true`
4. Render 서비스의 Deploy Hook URL을 복사합니다.
5. GitHub 저장소 Settings > Secrets and variables > Actions에 아래 secret을 저장합니다.
   - `RENDER_DEPLOY_HOOK_URL`: Render Deploy Hook URL
   - `SANTECH_APP_URL`: Render 앱 URL. 예: `https://santech-manager.onrender.com`
   - `SANTECH_CRON_SECRET`: Render 환경변수에 넣은 값과 같은 문자열
6. 이후 `main` 브랜치에 push하면 GitHub Actions가 문법 검사를 실행하고 Render 배포를 호출합니다.
7. 매일 한국 시간 오전 9시에 GitHub Actions가 `/api/tasks/daily-email`을 호출해, 메일 서비스를 활성화한 사용자에게 대시보드 요약을 보냅니다.

기본 ID는 `SANTECH_DEFAULT_USERNAME=sago87`로 설정되어 있습니다. 비밀번호는 저장소에 커밋하지 않습니다.

Render 무료 Web Service는 SMTP 포트가 막힐 수 있으므로, 무료 운영에서는 `RESEND_API_KEY`를 넣어 Resend HTTP API로 보내는 방식을 권장합니다. `onboarding@resend.dev` 발신자는 Resend 계정 소유 메일로만 테스트 발송할 수 있고, 다른 수신자에게 보내려면 Resend에서 도메인을 인증한 뒤 `RESEND_FROM`을 인증한 도메인 주소로 바꿔야 합니다.

Gmail SMTP를 쓰는 경우 일반 로그인 비밀번호가 아니라 Google 계정의 앱 비밀번호를 `SMTP_PASSWORD`에 넣어야 합니다.

## API 목록

- `GET /api/dashboard`: 누적 수익, 이번 달 수익, 누적 마일리지, 평균 마일 단가. 대시보드 누적 마일리지는 대한항공, 아시아나, 하나마일만 합산합니다.
- `GET /api/monthly`: 시드 월별 요약과 라이브 거래를 합산한 월별 집계
- `GET /api/santech?month=YYYY-MM`: 상테크 월별 요약 및 거래 목록
- `POST /api/santech`: 2026-07 이후 상테크 거래 생성
- `PATCH /api/santech/{id}/refund`: 2026-07 이후 상테크 거래 환급처와 환급 금액 입력 또는 수정
- `DELETE /api/santech/{id}`: 2026-07 이후 상테크 거래 삭제
- `GET /api/cream`: 크림/솔드아웃 시드 요약 및 라이브 거래 목록
- `POST /api/cream`: 2026-07 이후 크림/솔드아웃 거래 생성
- `DELETE /api/cream/{id}`: 2026-07 이후 크림/솔드아웃 거래 삭제
- `GET /api/mileage`: 누적 마일리지, 연도별 적립, 기본 환산 단가

## 주요 계산식

- 상테크 수익: `환급 + 포인트 + 캐시백 - 매매`
- 크림/솔드아웃 수익: `판매 - 구매 + 페이백`
- 월 총수익: `상테크 수익 + 크림/솔드아웃 수익`
- 월 총마일: `대한항공 + 아시아나 + 하나마일`
- 월 마일단가: `abs(상테크 수익) / 월 총마일`
- 평균 마일단가: `abs(누적 상테크 수익) / 누적 총마일`

## 상테크 카드 자동 계산

상테크 거래 저장 시 포인트, 청구할인, 하나마일은 서버에서 카드 기준으로 다시 계산합니다.

- `MG`: 월 할인금액 60,000원 한도 내에서 10% 할인
- `하나마일`: 1,500원당 1.6 하나마일 적립
- `any`: 월 할인금액 100,000원 한도 내에서 1.7% 할인
- `원더`: 한도 없이 1.2% 할인
- `행복`: 한도 없이 1.5% 포인트 적립

상테크 거래를 처음 저장할 때는 환급처와 환급액을 입력하지 않습니다. 실제 환급 후 거래 목록의 환급 정보 칸에서 환급처와 환급액을 나중에 반영합니다. 체크박스로 여러 거래를 선택하면 같은 환급 정보를 일괄 입력할 수 있고, 환급완료/미환급 필터로 목록을 나눠 볼 수 있습니다.
상테크 입력 시 `갯수`를 1 이상으로 지정하면 같은 조건의 거래를 여러 건 한 번에 생성합니다.
구매상품은 5개 고정 선택지로 관리하고, 환급처는 기본 선택지 외에 직접입력으로도 저장할 수 있습니다. 환급처 기본 선택지는 `포인트로페이`, `페이즈`, `마일캐시`, `원천`, `골드`, `팔라고`, `GLN`입니다.
선택한 상테크 월에는 카드별 누적 사용량도 함께 표시됩니다.
대시보드의 `당월 포함` 체크박스로 누적 수익과 누적 마일리지 계산에 현재 월을 포함할지 선택할 수 있습니다.

## 주의사항

- `monthly_summary`는 2026년 시드 데이터 전용 읽기 테이블입니다.
- 앱 시작 시 2026년 이전 `monthly_summary`, 거래, 이월 마일리지 데이터는 정리됩니다.
- 2026-06 이하 월은 화면에서 읽기 전용이며 POST/DELETE API도 403을 반환합니다.
- 2026-07 이후 입력 데이터는 `santech_transactions`, `cream_transactions`에만 저장됩니다.
- 입력 수익은 클라이언트 값이 아니라 서버에서 다시 계산합니다.
- 사용자 입력 메모와 조건은 화면 렌더링 시 HTML 이스케이프 처리됩니다.

## 검증 명령

```bash
python -m compileall .
python -c "import main; print('app import ok')"
```
