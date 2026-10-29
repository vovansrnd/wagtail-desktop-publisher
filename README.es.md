# wagtail-desktop-publisher

**Publica artículos Markdown e imágenes locales desde el escritorio a Wagtail mediante solicitudes API autenticadas. Incluye CLI y GUI, conserva los archivos Markdown locales y omite contenido sin cambios usando hashes.**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## Funciones principales

- Crear/actualizar borradores o publicar páginas desde Markdown y frontmatter YAML.
- Subir imágenes locales y reutilizar archivos idénticos por contenido.
- Guardar IDs de páginas Wagtail, estado de sincronización y metadatos en el frontmatter.
- CLI para scripts/SSH y GUI para trabajo interactivo.

## Requisitos y compatibilidad

- Dependencias declaradas: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- La compatibilidad de Python, Django y Wagtail debe verificarse en conjunto. La dependencia mínima del paquete no confirma que todas las versiones estén soportadas.

El cliente de escritorio depende de `requests`, `python-frontmatter`, `markdown` y `customtkinter`; no necesita instalar Wagtail en el equipo del editor. El servidor debe permitir escrituras autenticadas mediante la API v3. La documentación original indica Wagtail 7.0+ y pruebas con 8.0; no se garantizan versiones futuras.

## Instalación

Instala el paquete en el mismo entorno virtual que tu proyecto Wagtail:

```bash
pip install wagtail-desktop-publisher
```

Añade las aplicaciones en el orden indicado y conserva las demás dependencias del proyecto:


## Configuración inicial

Ejemplo mínimo para empezar. Adapta los nombres de modelos, campos API y URL a tu configuración.

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

El frontmatter suele incluir `title`, un `slug` estable, `excerpt`, `date` y, opcionalmente, `year`, `tags` e identificadores de categorías. Los campos disponibles dependen del esquema API del modelo de página. `/api/v3/publisher-images/` es un endpoint personalizado que Wagtail no proporciona por defecto: regístrelo en el servidor o configure otro endpoint seguro.




## Ajustes y comportamiento importantes

El README en inglés de este directorio es la referencia canónica y contiene las tablas completas de opciones y ejemplos ampliados. Esta traducción cubre la configuración práctica y las advertencias de seguridad esenciales; consulta la referencia inglesa antes de cambiar opciones avanzadas.

Consulta la [versión inglesa del README](README.md) para ver la referencia completa de ajustes.

### Notas importantes

El sitio de destino debe exponer API v3 y `/api/v3/publisher-images/`; este endpoint de carga no existe automáticamente en todas las instalaciones de Wagtail. Usa un token con privilegios mínimos y prueba la sincronización masiva con una copia.

## Seguridad y operación

- Mantén las dependencias actualizadas. Para HTML escrito por usuarios, utiliza la limpieza y representación previstas; no muestres comentarios o publicaciones almacenadas con `|safe` incondicional.
- Comprueba migraciones y permisos con usuarios normales, restringidos, moderadores y administradores.
- En instalaciones multisitio, prueba cada dominio configurado y un host desconocido. Si no se encuentra un Site, la consulta nunca debe ampliarse a todos los sitios.
- Trata los tokens de API, las credenciales SMTP y las URL privadas como secretos. No los guardes en Git ni los incluyas en informes públicos.
- Haz copias de seguridad de la base de datos y de los medios antes de migraciones, movimientos masivos, importaciones o la primera publicación masiva. Prueba primero en staging.

## Combinaciones recomendadas

- `wagtail-image-directories` es el complemento principal para `year/slug` si el endpoint de carga usa ese modelo.
- El selector Prose no es necesario para publicar Markdown.

## Lista de verificación

- [ ] Instala la versión candidata en staging y anota las versiones de Python, Django, Wagtail y la base de datos.
- [ ] Ejecuta `python manage.py check` y las migraciones del paquete.
- [ ] Prueba el flujo principal con un usuario normal y otro restringido.
- [ ] Revisa registros, acceso, caché, copias de seguridad y recuperación.

El archivo supera comprobaciones estáticas de sintaxis y empaquetado, pero no se ha ejecutado aquí una prueba completa de integración Django/Wagtail. Trata la lista siguiente como un requisito previo a la publicación, no como una afirmación de que se han probado todas las combinaciones.

## Solución de problemas

Si el flujo no funciona, revisa la configuración de la app, las migraciones, el orden de URL, los permisos y los registros de Django. Compara la versión y el ejemplo con el README inglés.

## Licencia y soporte

MIT. No se pudo confirmar una dirección pública del repositorio durante esta auditoría. No inventes una URL de GitHub a partir del nombre del paquete; comprueba los enlaces de PyPI.

