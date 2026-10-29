# wagtail-desktop-publisher

**인증된 API 요청으로 데스크톱의 Markdown 글과 로컬 이미지를 Wagtail에 게시합니다. CLI와 GUI를 제공하고 로컬 Markdown 원본을 유지하며 해시를 사용해 변경되지 않은 콘텐츠를 건너뜁니다.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## 주요 기능

- Markdown 및 YAML frontmatter로 초안을 생성/갱신하거나 페이지 게시.
- 로컬 이미지를 업로드하고 내용이 동일한 파일 재사용.
- Wagtail 페이지 ID, 동기화 상태 및 메타데이터를 frontmatter에 저장.
- 스크립트/SSH용 CLI와 대화형 작업용 GUI.

## 요구 사항 및 호환성

- 선언된 종속성: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- Python, Django, Wagtail의 호환성은 함께 확인해야 합니다. 최소 종속성 버전은 모든 버전의 지원을 의미하지 않습니다.

데스크톱 클라이언트는 `requests`, `python-frontmatter`, `markdown`, `customtkinter`에 의존합니다. 편집자 컴퓨터에 Wagtail을 설치할 필요는 없습니다. 대상 서버는 인증된 Wagtail API v3 쓰기를 지원해야 합니다. 원래 문서는 Wagtail 7.0 이상과 8.0에서의 검증을 언급하지만 향후 버전을 보장하지 않습니다.

## 설치

Wagtail 프로젝트와 같은 가상 환경에 패키지를 설치하세요:

```bash
pip install wagtail-desktop-publisher
```

이 패키지는 데스크톱/CLI 클라이언트입니다. 일반적으로 편집자 컴퓨터의 별도 Python 환경에서 실행하며 서버 프로젝트의 `INSTALLED_APPS`에 추가하지 않습니다. 서버에는 호환되는 Wagtail API와 이미지 업로드 endpoint를 별도로 구성해야 합니다.


## 초기 설정

아래는 최소 시작 예제입니다. 모델 이름, API 필드, URL을 실제 구성에 맞추세요.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

frontmatter에는 보통 `title`, 고정된 `slug`, `excerpt`, `date`, 선택적으로 `year`, `tags`, 카테고리 ID가 포함됩니다. 사용 가능한 필드는 페이지 모델의 API 스키마에 따라 달라집니다. `/api/v3/publisher-images/`는 기본 Wagtail에 없는 사용자 정의 endpoint입니다. 서버에 등록하거나 안전한 대체 endpoint를 구성하세요.




## 중요 설정 및 동작

이 디렉터리의 영어 README가 정식 기준 문서이며 전체 설정 표와 자세한 예제를 포함합니다. 이 번역은 실제 설치 절차와 핵심 보안 주의사항을 다룹니다. 고급 설정을 변경하기 전에 영어 문서를 확인하세요.

전체 설정 참조는 [영문 README](README.md)를 확인하세요.

### 중요한 참고 사항

대상 사이트는 API v3 및 `/api/v3/publisher-images/`를 제공해야 합니다. 이 이미지 업로드 엔드포인트는 모든 Wagtail 설치에 기본 제공되지 않습니다. 최소 권한 토큰을 사용하고 기사 디렉터리 복사본에서 대량 동기화를 시험하세요.

## 보안 및 운영 지침

- 종속성을 최신 상태로 유지하세요. 사용자 작성 HTML에는 지정된 정리/렌더링 경로를 사용하고, 저장된 댓글이나 포럼 게시물을 무조건 `|safe`로 출력하지 마세요.
- 일반 사용자, 제한 사용자, 중재자, 관리자 계정으로 마이그레이션과 권한을 확인하세요.
- 멀티사이트 환경에서는 설정된 모든 도메인과 알 수 없는 호스트를 테스트하세요. Site를 찾지 못했을 때 조회 범위를 모든 사이트의 레코드로 넓혀서는 안 됩니다.
- API 토큰, SMTP 자격 증명, 비공개 URL은 비밀로 취급하세요. Git에 커밋하거나 공개 버그 보고서에 포함하지 마세요.
- 마이그레이션, 대량 이동, 가져오기 또는 최초 대량 게시 전에 데이터베이스와 미디어 파일을 백업하고 먼저 스테이징에서 실행하세요.

## 권장 조합

- 업로드 API가 이 이미지 모델과 통합되어 있다면 `wagtail-image-directories`가 `year/slug` 관리에 가장 적합합니다.
- Markdown 게시에는 Prose 이미지 선택기가 필요하지 않습니다.

## 검증 체크리스트

- [ ] 스테이징에 후보 버전을 설치하고 Python, Django, Wagtail 및 DB 버전을 기록하세요.
- [ ] `python manage.py check`와 패키지 마이그레이션을 실행하세요.
- [ ] 일반 사용자와 제한 사용자로 주요 흐름을 테스트하세요.
- [ ] 로그, 접근 제어, 캐시, 백업 및 복원 절차를 점검하세요.

이 아카이브는 정적 구문 및 패키징 검사를 통과했지만 현재 환경에서 Django/Wagtail 런타임 통합 테스트 전체를 실행하지는 못했습니다. 아래 목록은 모든 조합을 테스트했다는 주장이 아니라 출시 전 필수 확인 항목입니다.

## 문제 해결

흐름이 작동하지 않으면 앱 설정, 마이그레이션, URL 순서, 사용자 권한 및 Django 로그를 확인하세요. 패키지 버전과 예제를 영문 README와 비교하세요.

## 라이선스 및 지원

MIT. 이번 감사에서는 공개 upstream 저장소 URL을 확인하지 못했습니다. GitHub URL을 추측하지 말고 PyPI 프로젝트 링크를 확인하세요.

