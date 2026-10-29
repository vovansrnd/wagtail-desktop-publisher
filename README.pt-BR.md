# wagtail-desktop-publisher

**Publica artigos Markdown e imagens locais do computador para o Wagtail por meio de requisições de API autenticadas. Inclui CLI e interface gráfica, mantém os arquivos Markdown locais e ignora conteúdo inalterado usando hashes.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## Principais recursos

- Criar/atualizar rascunhos ou publicar páginas a partir de Markdown e frontmatter YAML.
- Enviar imagens locais, reutilizando arquivos com conteúdo idêntico.
- Manter IDs das páginas Wagtail, estado de sincronização e metadados no frontmatter.
- CLI para scripts/SSH e GUI para edição interativa.

## Requisitos e compatibilidade

- Dependências declaradas: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- A compatibilidade entre Python, Django e Wagtail deve ser verificada em conjunto. A dependência mínima do pacote não confirma suporte a todas as versões.

O cliente desktop depende de `requests`, `python-frontmatter`, `markdown` e `customtkinter`; não é necessário instalar Wagtail no computador do editor. O servidor deve permitir escrita autenticada pela API v3. A documentação original cita Wagtail 7.0+ e testes com 8.0, sem garantir versões futuras.

## Instalação

Instale o pacote no mesmo ambiente virtual do seu projeto Wagtail:

```bash
pip install wagtail-desktop-publisher
```

Adicione os apps nesta ordem, mantendo as demais dependências do projeto:


## Configuração inicial

Exemplo mínimo para começar. Adapte nomes de modelos, campos da API e URLs à sua configuração.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

O frontmatter costuma conter `title`, um `slug` estável, `excerpt`, `date` e, opcionalmente, `year`, `tags` e IDs de categorias. Os campos disponíveis dependem do esquema API do modelo de página. `/api/v3/publisher-images/` é um endpoint personalizado que não vem no Wagtail padrão: registre-o no servidor ou configure um endpoint seguro equivalente.




## Configurações e comportamento importantes

O README em inglês deste diretório é a referência canônica e contém as tabelas completas de opções e exemplos detalhados. Esta tradução cobre a configuração prática e os avisos essenciais de segurança; consulte a referência em inglês antes de alterar opções avançadas.

Consulte o [README em inglês](README.md) para a referência completa das configurações.

### Observações importantes

O site de destino precisa expor a API v3 e `/api/v3/publisher-images/`; esse endpoint de upload não existe automaticamente em toda instalação Wagtail. Use um token com privilégios mínimos e teste a sincronização em lote com uma cópia.

## Segurança e operação

- Mantenha as dependências atualizadas. Para HTML escrito por usuários, use o fluxo previsto de sanitização e renderização; não exiba comentários ou posts armazenados com `|safe` incondicional.
- Verifique migrações e permissões com usuários comuns, restritos, moderadores e administradores.
- Em instalações multissite, teste cada domínio configurado e um host desconhecido. Se nenhum Site for encontrado, a consulta não deve abranger registros de todos os sites.
- Trate tokens de API, credenciais SMTP e URLs privadas como segredos. Não os envie ao Git nem os inclua em relatórios públicos.
- Faça backup do banco de dados e dos arquivos de mídia antes de migrações, movimentações em lote, importações ou da primeira publicação em massa. Teste primeiro em staging.

## Combinações recomendadas

- `wagtail-image-directories` é o complemento principal para `year/slug` se o endpoint de upload usa esse modelo.
- O seletor Prose não é necessário para publicação Markdown.

## Lista de verificação

- [ ] Instale a versão candidata em staging e registre as versões de Python, Django, Wagtail e banco de dados.
- [ ] Execute `python manage.py check` e as migrações do pacote.
- [ ] Teste o fluxo principal com usuário comum e usuário restrito.
- [ ] Confira logs, acesso, cache, backups e restauração.

O arquivo passou pelas verificações estáticas de sintaxe e empacotamento, mas a integração completa com Django/Wagtail não foi executada neste ambiente. Trate a lista abaixo como requisito para o lançamento, não como prova de que todas as combinações foram testadas.

## Solução de problemas

Se o fluxo não funcionar, confira a configuração do app, migrações, ordem das URLs, permissões e logs do Django. Compare a versão e o exemplo com o README em inglês.

## Licença e suporte

MIT. Não foi possível confirmar o endereço público do repositório nesta auditoria. Não invente uma URL do GitHub; confira os links no PyPI.

