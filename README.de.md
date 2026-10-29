# wagtail-desktop-publisher

**Veröffentlicht Markdown-Artikel und lokale Bilder vom Desktop über authentifizierte API-Anfragen auf einer Wagtail-Site. Bietet CLI und GUI, bewahrt lokale Markdown-Dateien und überspringt unveränderte Inhalte anhand von Hashes.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## Wichtigste Funktionen

- Entwürfe erstellen/aktualisieren oder Seiten aus Markdown und YAML-Frontmatter veröffentlichen.
- Lokale Bilder hochladen und inhaltsidentische Dateien wiederverwenden.
- Wagtail-Seiten-IDs, Synchronisationsstatus und Metadaten im Frontmatter speichern.
- CLI für Skripte/SSH und GUI für interaktives Arbeiten.

## Voraussetzungen und Kompatibilität

- Deklarierte Abhängigkeiten: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- Die Kompatibilität von Python, Django und Wagtail muss gemeinsam geprüft werden. Die minimale Paketabhängigkeit bestätigt keine Unterstützung jeder Version.

Der Desktop-Client benötigt `requests`, `python-frontmatter`, `markdown` und `customtkinter`; Wagtail muss nicht auf dem Schreibrechner installiert sein. Der Zielserver muss authentifizierte Schreibzugriffe über Wagtail API v3 unterstützen. Die ursprüngliche Dokumentation nennt Wagtail 7.0+ und Tests mit 8.0; künftige Versionen sind damit nicht garantiert.

## Installation

Installieren Sie das Paket in derselben virtuellen Umgebung wie Ihr Wagtail-Projekt:

```bash
pip install wagtail-desktop-publisher
```

Dies ist ein Desktop-/CLI-Client. Er läuft normalerweise in einer separaten Python-Umgebung auf dem Rechner der Redaktion und gehört nicht in `INSTALLED_APPS` des Serverprojekts. Auf dem Server müssen eine kompatible Wagtail-API und ein Upload-Endpunkt für Bilder eingerichtet werden.


## Erste Konfiguration

Minimales Einstiegsbeispiel. Passen Sie Modellnamen, API-Felder und URLs an Ihre Konfiguration an.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

Das Frontmatter enthält üblicherweise `title`, einen stabilen `slug`, `excerpt`, `date` und optional `year`, `tags` sowie Kategorie-IDs. Verfügbare Felder hängen vom API-Schema des Seitenmodells ab. `/api/v3/publisher-images/` ist ein benutzerdefinierter Endpunkt und nicht standardmäßig in Wagtail enthalten: Registrieren Sie ihn auf dem Server oder konfigurieren Sie einen eigenen sicheren Endpunkt.




## Wichtige Einstellungen und Verhalten

Die englische README in diesem Verzeichnis ist die maßgebliche Referenz und enthält vollständige Einstellungstabellen und ausführliche Beispiele. Diese Übersetzung erklärt die praktische Einrichtung und die wichtigsten Sicherheitshinweise; konsultieren Sie vor Änderungen an erweiterten Einstellungen die englische Referenz.

Die vollständige Einstellungsreferenz finden Sie in der [englischen README](README.md).

### Wichtige Hinweise

Die Zielsite muss API v3 und den Endpunkt `/api/v3/publisher-images/` bereitstellen; dieser Upload-Endpunkt gehört nicht automatisch zu jeder Wagtail-Installation. Verwenden Sie ein Token mit minimalen Rechten und testen Sie die Massensynchronisierung mit einer Kopie.

## Sicherheit und Betrieb

- Halten Sie Abhängigkeiten aktuell. Verwenden Sie für nutzererstelltes HTML den vorgesehenen Bereinigungs- und Ausgabepfad; geben Sie gespeicherte Kommentare oder Forenbeiträge nicht bedingungslos mit `|safe` aus.
- Prüfen Sie Migrationen und Berechtigungen mit normalen, eingeschränkten Benutzern, Moderatoren und Administratoren.
- Testen Sie bei mehreren Wagtail-Sites jede konfigurierte Domain sowie einen unbekannten Host. Wenn keine Site gefunden wird, darf eine Abfrage nicht auf Datensätze aller Sites erweitert werden.
- Behandeln Sie API-Tokens, SMTP-Zugangsdaten und private URLs als Geheimnisse. Committen Sie diese nicht in Git und veröffentlichen Sie sie nicht in Fehlerberichten.
- Sichern Sie Datenbank und Mediendateien vor Migrationen, Massenverschiebungen, Importen oder der ersten Massenveröffentlichung. Testen Sie diese Vorgänge zuerst in Staging.

## Empfohlene Kombinationen

- `wagtail-image-directories` ist die beste Ergänzung für `year/slug`, sofern der Upload-Endpunkt dieses Modell verwendet.
- `wagtail-prose-editor-images` wird für Markdown-Publikation nicht benötigt.

## Checkliste zur Überprüfung

- [ ] Installieren Sie den Kandidaten in Staging und notieren Sie Python-, Django-, Wagtail- und Datenbankversionen.
- [ ] Führen Sie `python manage.py check` und die Paketmigrationen aus.
- [ ] Prüfen Sie den Hauptablauf mit einem normalen und einem eingeschränkten Benutzer.
- [ ] Prüfen Sie Logs, Zugriffskontrolle, Caching, Backups und Wiederherstellung.

Das Archiv besteht statische Syntax- und Packaging-Prüfungen; die vollständige Django-/Wagtail-Laufzeitintegration wurde in dieser Umgebung jedoch nicht getestet. Betrachten Sie die folgende Checkliste als Freigabekriterium und nicht als Behauptung, dass jede Versionskombination getestet wurde.

## Fehlerbehebung

Wenn der Ablauf nicht funktioniert, prüfen Sie App-Konfiguration, Migrationen, URL-Reihenfolge, Benutzerrechte und Django-Logs. Vergleichen Sie Paketversion und Beispiel mit der englischen README.

## Lizenz und Support

MIT. Eine öffentliche Repository-Adresse ließ sich in diesem Audit nicht bestätigen. Raten Sie keine GitHub-URL anhand des Paketnamens; prüfen Sie die PyPI-Projektlinks.

