# wagtail-desktop-publisher

**認証済み API リクエストを通じて、デスクトップから Wagtail へ Markdown 記事とローカル画像を公開します。CLI と GUI を提供し、ローカル Markdown を保持し、ハッシュで変更のない内容をスキップします。**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## 主な機能

- Markdown と YAML frontmatter から下書きの作成/更新やページ公開。
- ローカル画像をアップロードし、内容が同一のファイルを再利用。
- Wagtail ページ ID、同期状態、メタデータを frontmatter に保存。
- スクリプト/SSH 向け CLI と対話的作業向け GUI。

## 要件と互換性

- 宣言されている依存関係: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- Python、Django、Wagtail の互換性は組み合わせて確認してください。最低依存バージョンは全バージョンのサポートを意味しません。

デスクトップクライアントは `requests`、`python-frontmatter`、`markdown`、`customtkinter` に依存します。執筆用 PC に Wagtail をインストールする必要はありません。対象サーバーは Wagtail API v3 の認証済み書き込みに対応する必要があります。元の文書は Wagtail 7.0+ と 8.0 での確認を記載していますが、将来の版を保証しません。

## インストール

Wagtail プロジェクトと同じ仮想環境にパッケージをインストールします。

```bash
pip install wagtail-desktop-publisher
```

これはデスクトップ/CLI クライアントです。通常は編集者の PC 上の独立した Python 環境で実行します。サーバー側プロジェクトの `INSTALLED_APPS` には追加しないでください。サーバーでは互換性のある Wagtail API と画像アップロード endpoint を別途設定します。


## 初期設定

以下は最小の開始例です。モデル名、API フィールド、URL は実際の構成に合わせてください。

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

frontmatter には通常 `title`、固定した `slug`、`excerpt`、`date`、必要に応じて `year`、`tags`、カテゴリ ID を指定します。利用可能なフィールドはページモデルの API スキーマによります。`/api/v3/publisher-images/` は標準 Wagtail に含まれないカスタム endpoint です。サーバーに登録するか、安全な代替 endpoint を設定してください。




## 重要な設定と動作

このディレクトリの英語 README が正式な基準ドキュメントで、設定表と詳細例をすべて含みます。この翻訳では実際の導入手順と重要な安全上の注意を説明します。高度な設定を変更する前に英語版を確認してください。

設定の完全な一覧は[英語 README](README.md)を参照してください。

### 重要な注意事項

対象サイトは API v3 と `/api/v3/publisher-images/` を提供する必要があります。この画像アップロードエンドポイントは全 Wagtail に標準搭載されていません。最小権限のトークンを使い、記事ディレクトリのコピーで一括同期をテストしてください。

## セキュリティと運用

- 依存関係を最新に保ってください。ユーザー作成 HTML には定められたサニタイズ/レンダリング経路を使い、保存済みコメントやフォーラム投稿を無条件に `|safe` で表示しないでください。
- 通常ユーザー、制限ユーザー、モデレーター、管理者でマイグレーションと権限を確認してください。
- マルチサイト環境では、設定済みのすべてのホストと未設定のホストをテストしてください。Site を特定できない場合、全サイトのレコードに検索範囲を拡張してはいけません。
- API トークン、SMTP 認証情報、非公開 URL は秘密情報として扱ってください。Git にコミットしたり、公開の不具合報告に含めたりしないでください。
- マイグレーション、大量移動、インポート、初回の一括公開の前に、データベースとメディアファイルをバックアップし、まずステージングで実行してください。

## 推奨構成

- アップロード API が画像モデルを利用するなら、`wagtail-image-directories` は `year/slug` 管理に最適です。
- Markdown 公開に Prose 画像選択は不要です。

## 確認チェックリスト

- [ ] ステージングに候補版を導入し、Python、Django、Wagtail、DB の各バージョンを記録する。
- [ ] `python manage.py check` とパッケージのマイグレーションを実行する。
- [ ] 通常ユーザーと制限ユーザーで主要な操作を試す。
- [ ] ログ、アクセス制御、キャッシュ、バックアップ、復元を確認する。

このアーカイブは静的な構文・パッケージチェックに合格していますが、この環境では Django/Wagtail の完全な実行時統合テストを行っていません。以下の項目は全組み合わせのテスト済みという意味ではなく、リリース前の必須確認事項です。

## トラブルシューティング

動作しない場合は、アプリ設定、マイグレーション、URL の順序、ユーザー権限、Django ログを確認してください。パッケージ版と例を英語 README と照合してください。

## ライセンスとサポート

MIT. この監査では公開 upstream リポジトリ URL を確認できませんでした。GitHub URL を推測せず PyPI のプロジェクトリンクを確認してください。

