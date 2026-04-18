# 配置与数据说明

本文档说明子非鱼安全工具箱的配置文件、运行时目录结构以及发布时需要注意的数据边界。

## 1. 配置文件

### 1.1 `settings.example.ini`

仓库提供了示例配置文件 [settings.example.ini](../settings.example.ini)，用于说明可配置项。

当前包含的主要配置段：

- `[General]`：基础设置，例如主题
- `[paths]`：最近使用的导入路径
- `[sync]`：官方工具库同步地址与同步行为
- `[update]`：GitHub Release / manifest 更新源配置

### 1.2 运行时 `settings.ini`

程序真正读写的是运行时目录中的：

- `.runtime/settings.ini`

该文件会在程序启动后自动生成或迁移，用于保存：

- 当前主题
- 更新检查开关
- 最近导入路径
- 同步和更新相关设置

## 2. 运行时目录 `.runtime/`

程序启动时会自动准备 `.runtime/` 目录，用来保存本地运行态数据。

典型结构如下：

```text
.runtime/
├─ data/
│  ├─ tools.json
│  └─ tools/
├─ logs/
├─ resources/
│  ├─ icons/
│  └─ notes/
│     └─ _attachments/
├─ images/
├─ updates/
└─ settings.ini
```

说明：

- `data/`：运行时工具数据
- `resources/icons/`：运行时图标资源
- `resources/notes/`：Markdown 笔记
- `resources/notes/_attachments/`：笔记附件
- `updates/`：更新流程使用的临时目录
- `settings.ini`：运行时用户设置

`.runtime/` 属于本地运行数据，不应提交到 Git。

## 3. 仓库模板数据 vs 运行时数据

### 3.1 仓库模板数据

仓库中保留的是模板或种子数据：

- [data/categories.json](../data/categories.json)
- [data/tools.json](../data/tools.json)
- [resources/icons/](../resources/icons/)
- [resources/notes/](../resources/notes/)

这些文件会在首次运行时被复制或作为初始资源使用。

### 3.2 运行时真实数据

程序运行后，用户实际使用的数据通常位于：

- `.runtime/data/tools.json`
- `.runtime/data/tools/*.json`
- `.runtime/resources/notes/*.md`
- `.runtime/resources/notes/_attachments/`

其中：

- `.runtime/data/tools.json` 是运行时主工具数据
- `.runtime/data/tools/*.json` 是按类别拆分的镜像文件
- 笔记文件采用稳定命名 `tool_<id>.md`

## 4. 工具配置字段

工具数据中常见字段包括：

- `name`
- `path`
- `description`
- `category_id`
- `subcategory_id`
- `background_image`
- `icon`
- `is_favorite`
- `arguments`
- `working_directory`
- `run_in_terminal`
- `is_web_tool`
- `type_label`
- `custom_interpreter_path`
- `custom_interpreter_type`
- `sync_id`

说明：

- `path` 可以是本地路径、目录路径或网页 URL
- `working_directory` 用于指定运行时工作目录
- `arguments` 用于启动参数或终端命令
- `sync_id` 用于官方工具库同步匹配

## 5. 配置导入导出

程序支持原生配置导入导出。

### 5.1 导出配置

导出时会生成 schema 为 `zifeiyu-toolkit-tools` 的 JSON 文件。

导出的目标主要是“工具配置迁移”，通常包含：

- 工具名称
- 路径
- 描述
- 分类映射信息
- 图标 / 背景图
- 运行配置
- 收藏状态

### 5.2 导入配置

导入时会：

- 识别并读取原生 schema
- 自动跳过重复工具
- 根据分类名重新匹配分类和子分类

## 6. 天狐 2.0 导入

程序内置对天狐 2.0 导出 JSON 的兼容导入逻辑。

导入时会：

- 检查来源和版本
- 根据内置规则映射到当前分类体系
- 为导入工具打上来源标记
- 将无法识别的工具放入 `待分类（天狐导入）`

同时提供“一键删除天狐导入工具”的清理入口。

## 7. 官方工具库同步

`settings.example.ini` 中的 `[sync]` 段可配置远程工具库 JSON 地址，例如：

- `official_tools_url`
- `update_existing`

同步要求：

- 链接必须是 `http://` 或 `https://`
- JSON schema 需要兼容原生导出格式

如果你计划公开发布自己的“官方工具库”，建议使用不含本地绝对路径的模板数据。

## 8. 更新配置

`settings.example.ini` 中的 `[update]` 段包含更新源配置：

- `github_repo`
- `release_api_url`
- `asset_name`
- `manifest_url`
- `check_on_start`

程序支持两种更新信息来源：

- GitHub Release API
- 自定义 manifest URL

如果发布版本支持更新器，还会使用 `.runtime/updates/` 作为更新会话目录。

## 9. 发布与隐私边界

发布仓库或分享配置前，建议重点检查：

1. `data/tools.json` 不包含个人本地绝对路径
2. `.runtime/` 未提交
3. `resources/notes/` 不包含个人笔记或附件
4. 文档、截图、示例命令中未泄露个人路径
5. 远程同步地址、更新地址均为可公开访问的发布地址

推荐在发布前执行：

```powershell
python scripts/repo_sanity_check.py
```

该脚本会检查：

- 默认工具库是否为空
- 默认仓库是否包含用户笔记
- 文本文件中是否残留绝对路径

## 10. 适合开源发布的做法

推荐采用以下发布模式：

- `data/categories.json` 保留公共分类模板
- `data/tools.json` 保留空模板或占位数据
- 使用 `settings.example.ini` 提供可参考配置
- 让用户在本地运行后自动生成 `.runtime/`
- 将个人工具路径、个人笔记、附件和运行时缓存全部保留在本地
