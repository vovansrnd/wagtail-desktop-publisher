# wagtail-desktop-publisher

**Publie des articles Markdown et des images locales depuis un poste de travail vers Wagtail via des requêtes API authentifiées. Fournit une CLI et une interface graphique, conserve les sources Markdown locales et ignore le contenu inchangé grâce aux empreintes.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## Fonctionnalités principales

- Créer/mettre à jour des brouillons ou publier des pages depuis Markdown et frontmatter YAML.
- Téléverser des images locales en réutilisant les fichiers identiques par contenu.
- Conserver les ID de pages Wagtail, l’état de synchronisation et les métadonnées dans le frontmatter.
- CLI pour scripts/SSH et GUI pour la rédaction interactive.

## Prérequis et compatibilité

- Dépendances déclarées: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- La compatibilité de Python, Django et Wagtail doit être vérifiée conjointement. La dépendance minimale du paquet ne confirme pas que toutes les versions sont prises en charge.

Le client de bureau dépend de `requests`, `python-frontmatter`, `markdown` et `customtkinter` ; Wagtail n’a pas besoin d’être installé sur l’ordinateur de rédaction. Le serveur doit autoriser l’écriture authentifiée via l’API v3. La documentation d’origine mentionne Wagtail 7.0+ et des tests avec 8.0, sans garantir les versions futures.

## Installation

Installez le paquet dans le même environnement virtuel que votre projet Wagtail :

```bash
pip install wagtail-desktop-publisher
```

Il s’agit d’un client de bureau/CLI. Il s’exécute normalement dans un environnement Python distinct sur l’ordinateur de rédaction ; il ne doit pas être ajouté à `INSTALLED_APPS` du projet serveur. Le serveur doit disposer d’une API Wagtail compatible et d’un endpoint de téléversement d’images.


## Configuration initiale

Exemple minimal pour démarrer. Adaptez les noms de modèles, les champs API et les URL à votre configuration.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

Le frontmatter contient généralement `title`, un `slug` stable, `excerpt`, `date` et éventuellement `year`, `tags` et des identifiants de catégories. Les champs disponibles dépendent du schéma API du modèle de page. `/api/v3/publisher-images/` est un endpoint personnalisé absent de Wagtail par défaut : enregistrez-le sur le serveur ou configurez un endpoint sécurisé équivalent.




## Paramètres et comportement importants

Le README anglais de ce répertoire est la référence canonique et contient les tableaux complets des options et les exemples détaillés. Cette traduction couvre la mise en place pratique et les avertissements de sécurité essentiels ; consultez la référence anglaise avant de modifier les options avancées.

Consultez le [README en anglais](README.md) pour la référence complète des paramètres.

### Points importants

Le site cible doit exposer l’API v3 et `/api/v3/publisher-images/` ; cet endpoint d’upload n’existe pas automatiquement dans chaque installation Wagtail. Utilisez un jeton à privilèges minimaux et testez la synchronisation massive sur une copie.

## Sécurité et exploitation

- Maintenez les dépendances à jour. Pour le HTML utilisateur, utilisez le chemin prévu de nettoyage et de rendu ; n’affichez pas les commentaires ou messages stockés avec un `|safe` inconditionnel.
- Vérifiez migrations et autorisations avec des utilisateurs normaux, restreints, modérateurs et administrateurs.
- En environnement multisite, testez chaque domaine configuré ainsi qu’un hôte inconnu. Si aucun Site n’est trouvé, une requête ne doit jamais s’élargir à tous les sites.
- Traitez les jetons API, identifiants SMTP et URL privées comme des secrets. Ne les committez pas dans Git et ne les publiez pas dans les rapports de bug.
- Sauvegardez la base de données et les fichiers médias avant les migrations, déplacements en masse, imports ou première publication en masse. Testez d’abord en préproduction.

## Combinaisons recommandées

- `wagtail-image-directories` est le complément principal pour `year/slug` si l’endpoint d’upload utilise ce modèle.
- Le sélecteur Prose n’est pas nécessaire pour publier du Markdown.

## Liste de vérification

- [ ] Installez la version candidate en préproduction et notez les versions de Python, Django, Wagtail et de la base de données.
- [ ] Exécutez `python manage.py check` et les migrations du paquet.
- [ ] Testez le flux principal avec un utilisateur normal et un utilisateur restreint.
- [ ] Vérifiez journaux, accès, cache, sauvegardes et restauration.

L’archive passe les contrôles statiques de syntaxe et de packaging, mais l’intégration Django/Wagtail complète n’a pas été exécutée dans cet environnement. Considérez la liste ci-dessous comme une condition de publication, et non comme la preuve que toutes les combinaisons sont testées.

## Dépannage

Si le flux ne fonctionne pas, vérifiez la configuration de l’application, les migrations, l’ordre des URL, les autorisations et les journaux Django. Comparez la version et l’exemple avec le README anglais.

## Licence et assistance

MIT. L’adresse publique du dépôt n’a pas pu être confirmée lors de cet audit. N’inventez pas d’URL GitHub ; vérifiez les liens du projet sur PyPI.

