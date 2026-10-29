# wagtail-desktop-publisher

**Publikuje artykuły Markdown i lokalne obrazy z komputera do Wagtail przez uwierzytelnione żądania API. Oferuje CLI i GUI, zachowuje lokalne pliki Markdown i pomija niezmienioną treść na podstawie hashy.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## Najważniejsze funkcje

- Tworzenie/aktualizowanie wersji roboczych lub publikowanie stron z Markdown i YAML frontmatter.
- Przesyłanie lokalnych obrazów z ponownym użyciem identycznych plików.
- Przechowywanie ID stron Wagtail, stanu synchronizacji i metadanych we frontmatter.
- CLI do skryptów/SSH oraz GUI do interaktywnej pracy.

## Wymagania i zgodność

- Zadeklarowane zależności: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- Zgodność Pythona, Django i Wagtail należy sprawdzać łącznie. Minimalna zależność pakietu nie potwierdza obsługi każdej wersji.

Klient desktopowy zależy od `requests`, `python-frontmatter`, `markdown` i `customtkinter`; Wagtail nie musi być zainstalowany na komputerze autora. Serwer musi obsługiwać uwierzytelniony zapis przez Wagtail API v3. Oryginalna dokumentacja wskazuje Wagtail 7.0+ i testy z 8.0, ale nie gwarantuje przyszłych wersji.

## Instalacja

Zainstaluj pakiet w tym samym środowisku wirtualnym co projekt Wagtail:

```bash
pip install wagtail-desktop-publisher
```

Dodaj aplikacje w tej kolejności, zachowując pozostałe zależności projektu:


## Pierwsza konfiguracja

Minimalny przykład na początek. Dostosuj nazwy modeli, pola API i adresy URL do swojej konfiguracji.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

Frontmatter zwykle zawiera `title`, stały `slug`, `excerpt`, `date` oraz opcjonalnie `year`, `tags` i identyfikatory kategorii. Dostępne pola zależą od schematu API modelu strony. `/api/v3/publisher-images/` to niestandardowy endpoint, którego nie ma w standardowym Wagtail: zarejestruj go na serwerze albo skonfiguruj własny bezpieczny endpoint.




## Ważne ustawienia i zachowanie

Angielski README w tym katalogu jest kanoniczną dokumentacją i zawiera pełne tabele opcji oraz rozszerzone przykłady. To tłumaczenie opisuje praktyczną konfigurację i najważniejsze ostrzeżenia bezpieczeństwa; przed zmianą zaawansowanych opcji sprawdź dokumentację angielską.

Pełną tabelę ustawień znajdziesz w [angielskim README](README.md).

### Ważne uwagi

Witryna docelowa musi udostępniać API v3 i `/api/v3/publisher-images/`; ten endpoint uploadu nie jest domyślnie dostępny w każdej instalacji Wagtail. Użyj tokenu z minimalnymi uprawnieniami i przetestuj synchronizację na kopii.

## Bezpieczeństwo i eksploatacja

- Aktualizuj zależności. Dla HTML użytkowników stosuj przewidziany mechanizm oczyszczania i renderowania; nie wyświetlaj zapisanych komentarzy ani postów bezwarunkowo przez `|safe`.
- Sprawdź migracje i uprawnienia jako zwykły, ograniczony użytkownik, moderator i administrator.
- W instalacji wieloserwisowej przetestuj każdą skonfigurowaną domenę i nieznany host. Brak Site nie może rozszerzać zapytania na rekordy wszystkich witryn.
- Traktuj tokeny API, dane SMTP i prywatne adresy URL jako sekrety. Nie dodawaj ich do Git ani do publicznych zgłoszeń.
- Wykonaj kopię zapasową bazy i plików multimedialnych przed migracjami, masowym przenoszeniem, importem lub pierwszą masową publikacją. Najpierw przetestuj te operacje na stagingu.

## Zalecane połączenia

- `wagtail-image-directories` to główne uzupełnienie dla `year/slug`, jeśli endpoint uploadu korzysta z tego modelu.
- Selektor Prose nie jest wymagany do publikacji Markdown.

## Lista kontrolna

- [ ] Zainstaluj wersję kandydującą na stagingu i zapisz wersje Pythona, Django, Wagtail oraz bazy.
- [ ] Uruchom `python manage.py check` i migracje pakietu.
- [ ] Przetestuj główny przepływ jako zwykły i ograniczony użytkownik.
- [ ] Sprawdź logi, dostęp, cache, kopie zapasowe i odtwarzanie.

Archiwum przechodzi statyczne kontrole składni i pakowania, ale w tym środowisku nie wykonano pełnych testów integracyjnych Django/Wagtail. Poniższą listę traktuj jako warunek wydania, a nie potwierdzenie przetestowania każdej kombinacji.

## Rozwiązywanie problemów

Jeśli przepływ nie działa, sprawdź konfigurację aplikacji, migracje, kolejność URL, uprawnienia i logi Django. Porównaj wersję pakietu i przykład z angielskim README.

## Licencja i pomoc

MIT. Nie udało się potwierdzić publicznego adresu repozytorium. Nie zgaduj URL GitHub; sprawdź linki na PyPI.

