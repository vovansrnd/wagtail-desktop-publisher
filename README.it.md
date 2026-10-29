# wagtail-desktop-publisher

**Pubblica articoli Markdown e immagini locali dal desktop a Wagtail tramite richieste API autenticate. Offre CLI e GUI, mantiene i file Markdown locali e salta i contenuti invariati tramite hash.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## Funzionalità principali

- Creare/aggiornare bozze o pubblicare pagine da Markdown e frontmatter YAML.
- Caricare immagini locali riutilizzando i file identici per contenuto.
- Memorizzare ID delle pagine Wagtail, stato di sincronizzazione e metadati nel frontmatter.
- CLI per script/SSH e GUI per il lavoro interattivo.

## Requisiti e compatibilità

- Dipendenze dichiarate: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- La compatibilità di Python, Django e Wagtail va verificata congiuntamente. La dipendenza minima del pacchetto non conferma il supporto di tutte le versioni.

Il client desktop dipende da `requests`, `python-frontmatter`, `markdown` e `customtkinter`; Wagtail non deve essere installato sul computer dell’autore. Il server deve consentire scritture autenticate tramite API v3. La documentazione originale indica Wagtail 7.0+ e test con 8.0, senza garantire le versioni future.

## Installazione

Installa il pacchetto nello stesso ambiente virtuale del progetto Wagtail:

```bash
pip install wagtail-desktop-publisher
```

Aggiungi le app nell’ordine indicato mantenendo le altre dipendenze del progetto:


## Configurazione iniziale

Esempio minimo per iniziare. Adatta nomi dei modelli, campi API e URL alla tua configurazione.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

Il frontmatter contiene di solito `title`, uno `slug` stabile, `excerpt`, `date` e, facoltativamente, `year`, `tags` e ID delle categorie. I campi disponibili dipendono dallo schema API del modello pagina. `/api/v3/publisher-images/` è un endpoint personalizzato non incluso in Wagtail standard: registrarlo sul server oppure configurare un endpoint sicuro equivalente.




## Impostazioni e comportamento importanti

Il README inglese in questa directory è il riferimento canonico e contiene le tabelle complete delle opzioni e gli esempi estesi. Questa traduzione copre la configurazione pratica e gli avvisi di sicurezza essenziali; consulta il riferimento inglese prima di modificare le opzioni avanzate.

Consulta il [README inglese](README.md) per la tabella completa delle impostazioni.

### Note importanti

Il sito di destinazione deve esporre API v3 e `/api/v3/publisher-images/`; questo endpoint di upload non è presente automaticamente in ogni installazione Wagtail. Usa un token con privilegi minimi e prova la sincronizzazione massiva su una copia.

## Sicurezza e operatività

- Mantieni aggiornate le dipendenze. Per l’HTML degli utenti usa il percorso previsto di sanificazione e rendering; non mostrare commenti o post salvati con `|safe` incondizionato.
- Verifica migrazioni e permessi con utenti normali, limitati, moderatori e amministratori.
- Nei progetti multi-sito, verifica ogni dominio configurato e un host sconosciuto. Se non viene trovato un Site, la query non deve estendersi ai record di tutti i siti.
- Tratta token API, credenziali SMTP e URL privati come segreti. Non inserirli in Git né in segnalazioni pubbliche.
- Esegui il backup del database e dei file multimediali prima di migrazioni, spostamenti in blocco, importazioni o pubblicazioni massive iniziali. Prova prima in staging.

## Combinazioni consigliate

- `wagtail-image-directories` è il complemento principale per `year/slug` se l’endpoint di upload usa questo modello.
- Il selettore Prose non è necessario per la pubblicazione Markdown.

## Lista di verifica

- [ ] Installa la versione candidata in staging e annota le versioni di Python, Django, Wagtail e database.
- [ ] Esegui `python manage.py check` e le migrazioni del pacchetto.
- [ ] Prova il flusso principale con un utente normale e uno limitato.
- [ ] Controlla log, accessi, cache, backup e ripristino.

L’archivio supera i controlli statici di sintassi e packaging, ma in questo ambiente non è stato eseguito un test completo d’integrazione Django/Wagtail. Considera la lista seguente un requisito per il rilascio, non la prova che ogni combinazione sia stata testata.

## Risoluzione dei problemi

Se il flusso non funziona, controlla configurazione dell’app, migrazioni, ordine URL, permessi e log Django. Confronta versione ed esempio con il README inglese.

## Licenza e supporto

MIT. Non è stato possibile confermare l’URL pubblico del repository durante questo audit. Non indovinare un URL GitHub; verifica i collegamenti PyPI.

