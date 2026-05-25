# 发布检查清单

发布前建议按下面顺序做一次快速检查，避免把本地运行数据、个人路径或不可复现的产物带进公开仓库。

## 1. 数据边界

- 确认 `.runtime/` 没有被提交。
- 确认 `data/tools.json` 只包含模板或可公开的工具配置。
- 确认 `resources/notes/` 没有个人笔记，`resources/notes/_attachments/` 没有个人附件。
- 确认文档、截图、配置示例中没有个人绝对路径、账号、Token 或内网地址。

## 2. 本地验证

```powershell
python scripts/repo_sanity_check.py
python -m unittest discover -s tests -v
```

如果本机使用 pyenv，请先设置可用版本：

```powershell
pyenv local 3.12.7
```

## 3. 打包检查

- 确认程序版本、README 当前版本、更新日志版本和发布包版本一致，例如 `v3.2.3`。
- 确认 `settings.example.ini` 中的同步源和更新源指向公开可访问地址。
- 确认发布包内包含打包入口 `ZifeiyuSec.exe`、运行时依赖、`data/`、`resources/`、`images/`、`docs/`。
- 确认发布包不会覆盖用户本地的 `.runtime/` 数据。
- 确认 `release/`、`build/`、`dist/` 等构建产物不直接提交到源码仓库。

推荐使用明确版本号打包：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_release.ps1 -Version 3.2.3 -Clean -SmokeTest -StopRunningApp
```

## 4. 更新流程

- 如果启用 GitHub / Gitee Release 更新，确认两个平台的 tag、zip 资源名、zip SHA256 和 `settings.example.ini` 中的配置一致。
- 如果同时维护 GitHub 和 Gitee，确认代码、tag 和 Release 附件已经同步推送。
- 如果启用 manifest 更新，确认 manifest 至少包含 `version` 和 `download_url`。
- 如果提供 `sha256`，确认它对应最终发布 zip 文件。

## 5. 发布后回归

- 从干净目录解压发布包并启动 `python main.py` 或打包后的可执行文件。
- 首次启动后确认 `.runtime/` 自动生成。
- 添加、编辑、删除工具各验证一次。
- 验证网页工具、本地目录、本地文件、终端工具的启动行为。
- 验证笔记保存、搜索、导入导出、体检、检查更新入口。
