#!/usr/bin/env python3
"""Сборка locale/<lang>/LC_MESSAGES/wagtail_desktop_publisher.mo из каталога
CATALOG ниже. Запускается вручную при изменении строк: не требует msgfmt —
.mo пишется собственным компилятором (стандартный формат GNU gettext).
"""
import os
import struct

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = "wagtail_desktop_publisher"
DOMAIN = PACKAGE

# source (en) -> перевод по языкам
CATALOG = {
    "Wagtail Desktop Publisher": {
        "ru": "Wagtail Desktop Publisher",
        "de": "Wagtail Desktop Publisher",
        "es": "Wagtail Desktop Publisher",
        "fr": "Wagtail Desktop Publisher",
        "it": "Wagtail Desktop Publisher",
        "pt_BR": "Wagtail Desktop Publisher",
        "nl": "Wagtail Desktop Publisher",
        "pl": "Wagtail Desktop Publisher",
        "tr": "Wagtail Desktop Publisher",
        "zh_CN": "Wagtail Desktop Publisher",
        "ja": "Wagtail Desktop Publisher",
        "ko": "Wagtail Desktop Publisher",
    },
    "Connect": {
        "ru": "Подключиться",
        "de": "Verbinden",
        "es": "Conectar",
        "fr": "Se connecter",
        "it": "Connetti",
        "pt_BR": "Conectar",
        "nl": "Verbinden",
        "pl": "Połącz",
        "tr": "Bağlan",
        "zh_CN": "连接",
        "ja": "接続",
        "ko": "연결",
    },
    "API URL": {
        "ru": "URL API",
        "de": "API-URL",
        "es": "URL de la API",
        "fr": "URL de l'API",
        "it": "URL API",
        "pt_BR": "URL da API",
        "nl": "API-URL",
        "pl": "URL API",
        "tr": "API URL",
        "zh_CN": "API 地址",
        "ja": "API URL",
        "ko": "API URL",
    },
    "Token": {
        "ru": "Токен",
        "de": "Token",
        "es": "Token",
        "fr": "Jeton",
        "it": "Token",
        "pt_BR": "Token",
        "nl": "Token",
        "pl": "Token",
        "tr": "Token",
        "zh_CN": "令牌",
        "ja": "トークン",
        "ko": "토큰",
    },
    "Connected sites": {
        "ru": "Подключённые сайты",
        "de": "Verbundene Websites",
        "es": "Sitios conectados",
        "fr": "Sites connectés",
        "it": "Siti connessi",
        "pt_BR": "Sites conectados",
        "nl": "Verbonden sites",
        "pl": "Połączone witryny",
        "tr": "Bağlı siteler",
        "zh_CN": "已连接站点",
        "ja": "接続済みサイト",
        "ko": "연결된 사이트",
    },
    "Article file (.md)": {
        "ru": "Файл статьи (.md)",
        "de": "Artikeldatei (.md)",
        "es": "Archivo del artículo (.md)",
        "fr": "Fichier de l'article (.md)",
        "it": "File articolo (.md)",
        "pt_BR": "Arquivo do artigo (.md)",
        "nl": "Artikelbestand (.md)",
        "pl": "Plik artykułu (.md)",
        "tr": "Makale dosyası (.md)",
        "zh_CN": "文章文件 (.md)",
        "ja": "記事ファイル (.md)",
        "ko": "글 파일 (.md)",
    },
    "Path to the article": {
        "ru": "Путь к статье",
        "de": "Pfad zum Artikel",
        "es": "Ruta al artículo",
        "fr": "Chemin de l'article",
        "it": "Percorso dell'articolo",
        "pt_BR": "Caminho do artigo",
        "nl": "Pad naar het artikel",
        "pl": "Ścieżka do artykułu",
        "tr": "Makale yolu",
        "zh_CN": "文章路径",
        "ja": "記事のパス",
        "ko": "글 경로",
    },
    "Title": {
        "ru": "Заголовок",
        "de": "Titel",
        "es": "Título",
        "fr": "Titre",
        "it": "Titolo",
        "pt_BR": "Título",
        "nl": "Titel",
        "pl": "Tytuł",
        "tr": "Başlık",
        "zh_CN": "标题",
        "ja": "タイトル",
        "ko": "제목",
    },
    "Slug (URL)": {
        "ru": "Slug (URL)",
        "de": "Slug (URL)",
        "es": "Slug (URL)",
        "fr": "Slug (URL)",
        "it": "Slug (URL)",
        "pt_BR": "Slug (URL)",
        "nl": "Slug (URL)",
        "pl": "Slug (URL)",
        "tr": "Slug (URL)",
        "zh_CN": "Slug (URL)",
        "ja": "Slug (URL)",
        "ko": "Slug (URL)",
    },
    "Year": {
        "ru": "Год",
        "de": "Jahr",
        "es": "Año",
        "fr": "Année",
        "it": "Anno",
        "pt_BR": "Ano",
        "nl": "Jaar",
        "pl": "Rok",
        "tr": "Yıl",
        "zh_CN": "年份",
        "ja": "年",
        "ko": "연도",
    },
    "Publish immediately (otherwise save as draft)": {
        "ru": "Опубликовать сразу (иначе сохранить как черновик)",
        "de": "Sofort veröffentlichen (sonst als Entwurf speichern)",
        "es": "Publicar de inmediato (si no, guardar como borrador)",
        "fr": "Publier immédiatement (sinon enregistrer comme brouillon)",
        "it": "Pubblica subito (altrimenti salva come bozza)",
        "pt_BR": "Publicar imediatamente (senão salvar como rascunho)",
        "nl": "Direct publiceren (anders als concept opslaan)",
        "pl": "Opublikuj od razu (w przeciwnym razie zapisz jako szkic)",
        "tr": "Hemen yayınla (aksi halde taslak olarak kaydet)",
        "zh_CN": "立即发布（否则保存为草稿）",
        "ja": "すぐに公開する（ otherwise 下書きとして保存）",
        "ko": "즉시 게시 (아니면 초안으로 저장)",
    },
    "Sync article to Wagtail": {
        "ru": "Синхронизировать статью в Wagtail",
        "de": "Artikel mit Wagtail synchronisieren",
        "es": "Sincronizar artículo con Wagtail",
        "fr": "Synchroniser l'article avec Wagtail",
        "it": "Sincronizza l'articolo con Wagtail",
        "pt_BR": "Sincronizar artigo com o Wagtail",
        "nl": "Artikel met Wagtail synchroniseren",
        "pl": "Zsynchronizuj artykuł z Wagtail",
        "tr": "Makaleyi Wagtail ile eşitle",
        "zh_CN": "将文章同步到 Wagtail",
        "ja": "記事をWagtailへ同期",
        "ko": "Wagtail에 글 동기화",
    },
    "Images": {
        "ru": "Картинки",
        "de": "Bilder",
        "es": "Imágenes",
        "fr": "Images",
        "it": "Immagini",
        "pt_BR": "Imagens",
        "nl": "Afbeeldingen",
        "pl": "Obrazy",
        "tr": "Görseller",
        "zh_CN": "图片",
        "ja": "画像",
        "ko": "이미지",
    },
    "Language": {
        "ru": "Язык",
        "de": "Sprache",
        "es": "Idioma",
        "fr": "Langue",
        "it": "Lingua",
        "pt_BR": "Idioma",
        "nl": "Taal",
        "pl": "Język",
        "tr": "Dil",
        "zh_CN": "语言",
        "ja": "言語",
        "ko": "언어",
    },
    "Site": {
        "ru": "Сайт",
        "de": "Website",
        "es": "Sitio",
        "fr": "Site",
        "it": "Sito",
        "pt_BR": "Site",
        "nl": "Site",
        "pl": "Witryna",
        "tr": "Site",
        "zh_CN": "站点",
        "ja": "サイト",
        "ko": "사이트",
    },
    "Section": {
        "ru": "Раздел",
        "de": "Bereich",
        "es": "Sección",
        "fr": "Section",
        "it": "Sezione",
        "pt_BR": "Seção",
        "nl": "Sectie",
        "pl": "Sekcja",
        "tr": "Bölüm",
        "zh_CN": "栏目",
        "ja": "セクション",
        "ko": "섹션",
    },
    "Scan": {
        "ru": "Проверить",
        "de": "Prüfen",
        "es": "Escanear",
        "fr": "Analyser",
        "it": "Scansiona",
        "pt_BR": "Verificar",
        "nl": "Scannen",
        "pl": "Skanuj",
        "tr": "Tara",
        "zh_CN": "扫描",
        "ja": "スキャン",
        "ko": "스캔",
    },
    "Connection error": {
        "ru": "Ошибка подключения",
        "de": "Verbindungsfehler",
        "es": "Error de conexión",
        "fr": "Erreur de connexion",
        "it": "Errore di connessione",
        "pt_BR": "Erro de conexão",
        "nl": "Verbindingsfout",
        "pl": "Błąd połączenia",
        "tr": "Bağlantı hatası",
        "zh_CN": "连接错误",
        "ja": "接続エラー",
        "ko": "연결 오류",
    },
    "Article synced successfully": {
        "ru": "Статья успешно синхронизирована",
        "de": "Artikel erfolgreich synchronisiert",
        "es": "Artículo sincronizado con éxito",
        "fr": "Article synchronisé avec succès",
        "it": "Articolo sincronizzato con successo",
        "pt_BR": "Artigo sincronizado com sucesso",
        "nl": "Artikel succesvol gesynchroniseerd",
        "pl": "Artykuł pomyślnie zsynchronizowany",
        "tr": "Makale başarıyla eşitlendi",
        "zh_CN": "文章同步成功",
        "ja": "記事の同期に成功しました",
        "ko": "글이 성공적으로 동기화되었습니다",
    },
    "Page tree": {
        "ru": "Дерево страниц",
        "de": "Seitenbaum",
        "es": "Árbol de páginas",
        "fr": "Arborescence des pages",
        "it": "Albero delle pagine",
        "pt_BR": "Árvore de páginas",
        "nl": "Paginaboom",
        "pl": "Drzewo stron",
        "tr": "Sayfa ağacı",
        "zh_CN": "页面树",
        "ja": "ページツリー",
        "ko": "페이지 트리",
    },
}


def _make_mo(translation: dict[str, str]) -> bytes:
    """Компилятор GNU .mo — по алгоритмуcanonical Tools/i18n/msgfmt.py."""
    keys = sorted(translation)
    offsets = []
    ids = b""
    strs = b""
    for k in keys:
        idb = k.encode("utf-8")
        strb = translation[k].encode("utf-8")
        offsets.append((len(ids), len(idb), len(strs), len(strb)))
        ids += idb + b"\x00"
        strs += strb + b"\x00"
    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)
    koffsets = []
    voffsets = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, keystart + o1]
        voffsets += [l2, valuestart + o2]
    output = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + n * 8, keystart, valuestart)
    output += struct.pack(f"{len(koffsets)}i", *koffsets)
    output += struct.pack(f"{len(voffsets)}i", *voffsets)
    return output + ids + strs


def main():
    for code, _label in [
        ("ru", ""), ("de", ""), ("es", ""), ("fr", ""), ("it", ""), ("pt_BR", ""),
        ("nl", ""), ("pl", ""), ("tr", ""), ("zh_CN", ""), ("ja", ""), ("ko", ""),
    ]:
        translation = {src: tr[code] for src, tr in CATALOG.items() if tr.get(code)}
        # ВАЖНО: в .mo заголовок содержит РЕАЛЬНЫЕ байты новой строки —
        # gettext._parse разбивает его по b'\n' и ищет charset
        translation[""] = (
            f"Project-Id-Version: {PACKAGE}\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/plain; charset=UTF-8\n"
            "Content-Transfer-Encoding: 8bit\n"
        )
        out_dir = os.path.join(BASE, "locale", code, "LC_MESSAGES")
        os.makedirs(out_dir, exist_ok=True)
        mo = _make_mo(translation)
        with open(os.path.join(out_dir, f"{DOMAIN}.mo"), "wb") as fh:
            fh.write(mo)
        # .po-файл для правок человеком
        po_lines = ['msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"', ""]
        for src, tr in translation.items():
            if not src:
                continue
            po_lines += [f'msgid "{src}"', f'msgstr "{tr}"', ""]
        with open(os.path.join(out_dir, f"{DOMAIN}.po"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(po_lines))
        print(f"{code}: {len(translation) - 1} строк")
    print("готово")


if __name__ == "__main__":
    main()
