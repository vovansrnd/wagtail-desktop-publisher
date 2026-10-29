# wagtail-desktop-publisher

**通过经过身份验证的 API 请求，将桌面上的 Markdown 文章和本地图片发布到 Wagtail。提供 CLI 和 GUI，保留本地 Markdown 源文件，并使用哈希跳过未更改的内容。**

[English](README.md) · [Русский](README.ru.md) · [Deutsch](README.de.md) · [Español](README.es.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português (Brasil)](README.pt-BR.md) · [Nederlands](README.nl.md) · [Polski](README.pl.md) · [Türkçe](README.tr.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

## 主要功能

- 从 Markdown 和 YAML frontmatter 创建/更新草稿或发布页面。
- 上传本地图片，并复用内容完全相同的文件。
- 在 frontmatter 中记录 Wagtail 页面 ID、同步状态和元数据。
- 提供适用于脚本/SSH 的 CLI 及交互式 GUI。

## 依赖与兼容性

- 声明的依赖: `requests >= 2.28; python-frontmatter >= 1.0; markdown >= 3.5; customtkinter >= 5.2`.
- Python、Django 与 Wagtail 的兼容性必须一起验证。最低依赖版本并不代表所有版本均受支持。

桌面客户端依赖 `requests`、`python-frontmatter`、`markdown` 和 `customtkinter`；编辑者的电脑不需要安装 Wagtail。目标服务器必须支持通过 Wagtail API v3 进行经过身份验证的写入。原始文档提到 Wagtail 7.0+ 并在 8.0 上验证，但不保证未来版本。

## 安装

请在与 Wagtail 项目相同的虚拟环境中安装此包：

```bash
pip install wagtail-desktop-publisher
```

按以下顺序添加应用，同时保留项目原有的其他依赖：


## 初始配置

下面是最小起步示例。请根据项目调整模型名、API 字段和 URL。

```bash
wagtail-publisher init --url https://example.com/api/v3 --token YOUR_TOKEN --site example.com
wagtail-publisher publish articles/2026/example/index.md --parent 42
# Add --publish to publish immediately; test with a draft first.
wagtail-publisher status articles/
```

frontmatter 通常包含 `title`、稳定的 `slug`、`excerpt`、`date`，以及可选的 `year`、`tags` 和分类 ID。可用字段取决于页面模型的 API schema。`/api/v3/publisher-images/` 是自定义 endpoint，标准 Wagtail 默认不提供；请在服务器上注册它，或配置安全的替代 endpoint。




## 重要设置与行为

本目录中的英文 README 是规范参考文档，包含完整设置表和扩展示例。本译文覆盖实际安装步骤和关键安全注意事项；修改高级设置前请查阅英文文档。

完整设置说明请参阅[英文 README](README.md)。

### 重要注意事项

目标站点必须提供 API v3 和 `/api/v3/publisher-images/`；该图片上传接口并非每个 Wagtail 安装都默认提供。请使用权限最小化的令牌，并先在目录副本上测试批量同步。

## 安全与运维建议

- 请保持依赖更新。用户编写的 HTML 应使用预期的清理和渲染路径；不要无条件对已存储的评论或论坛帖子使用 `|safe`。
- 请分别使用普通用户、受限用户、版主和管理员验证迁移与权限。
- 多站点部署时，请测试每个已配置域名以及一个未知主机。找不到 Site 时，查询不得扩大为读取所有站点的数据。
- API 令牌、SMTP 凭据和私有 URL 都应视为机密。不要提交到 Git，也不要放入公开的问题报告。
- 执行迁移、批量移动、导入或首次批量发布之前，请备份数据库和媒体文件，并先在预发布环境测试。

## 推荐组合

- 若上传接口接入该图片模型，`wagtail-image-directories` 是管理 `year/slug` 的最佳搭档。
- Markdown 发布不需要 Prose 图片选择器。

## 验证清单

- [ ] 在预发布环境安装候选版本，并记录 Python、Django、Wagtail 和数据库版本。
- [ ] 运行 `python manage.py check` 和包迁移。
- [ ] 使用普通用户与受限用户测试主要流程。
- [ ] 检查日志、访问权限、缓存、备份和恢复。

本归档通过静态语法与打包检查，但当前环境未完成 Django/Wagtail 运行时集成测试。请将以下清单视为发布前的必检项目，而不是所有版本组合均已测试的声明。

## 故障排查

如果流程无法运行，请检查应用配置、迁移、URL 顺序、用户权限和 Django 日志，并将包版本与示例和英文 README 对照。

## 许可证与支持

MIT. 本次审查未能确认公开上游仓库地址。不要根据包名猜测 GitHub URL；请检查 PyPI 项目链接。

