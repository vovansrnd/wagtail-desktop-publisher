# wagtail-desktop-publisher

**Publiceert Markdown-artikelen en lokale afbeeldingen vanaf de desktop naar Wagtail via geauthenticeerde API-aanvragen. Biedt CLI en GUI, behoudt lokale Markdown-bronnen en slaat ongewijzigde inhoud over op basis van hashes.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## Belangrijkste functies

- Concepten maken/bijwerken of pagina’s publiceren vanuit Markdown en YAML-frontmatter.
- Lokale afbeeldingen uploaden en identieke bestanden hergebruiken.
- Wagtail-pagina-ID’s, synchronisatiestatus en metadata in frontmatter bewaren.
- CLI voor scripts/SSH en GUI voor interactief schrijven.

## Vereisten en compatibiliteit

- Gedeclareerde afhankelijkheden: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- Controleer de compatibiliteit van Python, Django en Wagtail gezamenlijk. De minimale pakketafhankelijkheid bewijst niet dat alle versies worden ondersteund.

De desktopclient gebruikt `requests`, `python-frontmatter`, `markdown` en `customtkinter`; Wagtail hoeft niet op de computer van de redacteur te worden geïnstalleerd. De server moet geauthenticeerde schrijfacties via Wagtail API v3 ondersteunen. De oorspronkelijke documentatie noemt Wagtail 7.0+ en tests met 8.0; toekomstige versies zijn niet gegarandeerd.

## Installatie

Installeer het pakket in dezelfde virtuele omgeving als je Wagtail-project:

```bash
pip install wagtail-desktop-publisher
```

Voeg de apps in deze volgorde toe en behoud de overige projectafhankelijkheden:


## Eerste configuratie

Minimaal startvoorbeeld. Pas modelnamen, API-velden en URL’s aan je configuratie aan.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

Frontmatter bevat meestal `title`, een stabiele `slug`, `excerpt`, `date` en optioneel `year`, `tags` en categorie-ID’s. Beschikbare velden hangen af van het API-schema van het paginamodel. `/api/v3/publisher-images/` is een aangepaste endpoint die niet standaard bij Wagtail hoort: registreer deze op de server of configureer een eigen veilige endpoint.




## Belangrijke instellingen en gedrag

De Engelse README in deze map is de canonieke referentie met volledige instellingstabellen en uitgebreide voorbeelden. Deze vertaling behandelt de praktische installatie en de belangrijkste veiligheidswaarschuwingen; raadpleeg de Engelse referentie voordat je geavanceerde instellingen wijzigt.

Raadpleeg de [Engelse README](README.md) voor het volledige instellingenoverzicht.

### Belangrijke aandachtspunten

De doelsite moet API v3 en `/api/v3/publisher-images/` aanbieden; dit uploadendpoint bestaat niet standaard in elke Wagtail-installatie. Gebruik een token met minimale rechten en test bulk-synchronisatie op een kopie.

## Beveiliging en beheer

- Houd afhankelijkheden bijgewerkt. Gebruik voor door gebruikers geschreven HTML het bedoelde opschonings- en renderpad; geef opgeslagen reacties of forumberichten niet onvoorwaardelijk weer met `|safe`.
- Controleer migraties en rechten met gewone, beperkte gebruikers, moderators en beheerders.
- Test bij meerdere sites elk ingesteld domein en een onbekende host. Als geen Site wordt gevonden, mag een query niet worden verbreed naar records van alle sites.
- Behandel API-tokens, SMTP-inloggegevens en privé-URL’s als geheimen. Commit ze niet naar Git en vermeld ze niet in openbare bugrapporten.
- Maak een back-up van database en mediabestanden vóór migraties, bulkverplaatsingen, imports of de eerste bulkpublicatie. Test zulke handelingen eerst in staging.

## Aanbevolen combinaties

- `wagtail-image-directories` is de belangrijkste aanvulling voor `year/slug` als het uploadendpoint dit model gebruikt.
- De Prose-kiezer is niet nodig voor Markdown-publicatie.

## Controlelijst

- [ ] Installeer de kandidaat in staging en noteer de Python-, Django-, Wagtail- en databaseversies.
- [ ] Voer `python manage.py check` en de pakketmigraties uit.
- [ ] Test de hoofdworkflow met een gewone en beperkte gebruiker.
- [ ] Controleer logs, toegang, caching, back-ups en herstel.

Het archief slaagt voor statische syntax- en packagingcontroles, maar volledige Django/Wagtail-runtime-integratie is hier niet uitgevoerd. Beschouw de lijst hieronder als vrijgavevoorwaarde, niet als bewijs dat elke combinatie is getest.

## Probleemoplossing

Als de workflow niet werkt, controleer appconfiguratie, migraties, URL-volgorde, gebruikersrechten en Django-logs. Vergelijk pakketversie en voorbeeld met de Engelse README.

## Licentie en ondersteuning

MIT. Een openbare upstream-URL kon niet worden bevestigd. Raad geen GitHub-URL op basis van de pakketnaam; controleer de PyPI-links.

