# 子非鱼工具箱 (ZifeiyuSec Toolkit)

一个现代化、功能齐全的渗透测试工具分类管理平台，专为安全测试人员设计，帮助快速组织和访问各种渗透测试工具。

## 📋 项目简介

子非鱼工具箱是一个基于PyQt5开发的Web网络安全工具管理系统，提供直观的图形界面，帮助安全测试人员更高效地管理和使用各类渗透测试工具。

### 核心优势

- **直观的图形界面**：现代化的UI设计，支持主题切换
- **灵活的工具管理**：支持添加、编辑、删除和搜索工具
- **分类管理系统**：支持多级分类，便于工具组织
- **自定义配置**：支持工具参数配置和工作目录设置
- **支持多种工具类型**：命令行工具和网页工具
- **使用统计**：自动记录工具使用次数和最后使用时间
- **隐藏终端运行**：支持通过VBS/BAT脚本隐藏终端窗口运行

## 🚀 快速开始

### 环境要求

- Python 3.8+
- PyQt5及相关依赖

### 使用方式

#### 方式1：直接运行（有Python环境）

1. **克隆仓库**
```bash
git clone https://github.com/zifeiyu-sec/zifeiyuSec-Toolkit.git
cd zifeiyuSec-Toolkit
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **运行应用**
```bash
python main.py
```

#### 方式2：创建桌面快捷方式（双击启动）

1. **克隆仓库**
```bash
git clone https://github.com/zifeiyu-sec/zifeiyuSec-Toolkit.git
cd zifeiyuSec-Toolkit
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **创建快捷方式**
```bash
python scripts/create_desktop_shortcut.py
```

4. **使用快捷方式**
   - 在桌面上找到名为"子非鱼工具箱.lnk"的快捷方式
   - 双击即可启动应用
   - 启动时无终端窗口显示
   - 图标使用`image.ico`

## 📋 主要功能

### 工具管理
- ✅ 添加新工具（命令行工具和网页工具）
- ✅ 编辑工具配置
- ✅ 删除工具
- ✅ 收藏常用工具
- ✅ 工具使用统计
- ✅ 工具搜索功能

### 分类管理
- ✅ 多级分类支持
- ✅ 分类图标自定义
- ✅ 分类编辑和删除

### 主题支持
- ✅ 蓝白主题
- ✅ 墨绿主题
- ✅ 主题切换功能

## 📸 效果图

### 蓝白主题

![蓝白主题](./images/README/image-20251128010917770.png)

### 墨绿主题

![墨绿主题](./images/README/image-20251128013809420.png)

## 📖 使用指南

### 添加工具

1. 点击左上角"新增工具"按钮
2. 填写工具基本信息（名称、路径、描述等）
3. 选择分类和子分类
4. 配置运行参数（可选）
5. 点击"保存"完成添加

### 编辑工具

1. 右键点击工具卡片
2. 选择"编辑工具"
3. 修改工具信息
4. 点击"保存"完成修改

### 搜索工具

1. 在搜索框中输入工具名称或标签
2. 系统会实时过滤显示匹配的工具

### 切换主题

1. 点击右上角的设置按钮
2. 选择"主题设置"
3. 在主题列表中选择喜欢的主题
4. 主题将立即切换

## 🛠️ 项目结构

```
zifeiyuSec-Toolkit/
├── core/                 # 核心功能模块
│   ├── app.py           # 应用主逻辑
│   ├── data_manager.py  # 数据管理
│   └── image_manager.py # 图片管理
├── ui/                   # UI组件
│   ├── category_view.py     # 分类视图
│   ├── subcategory_view.py  # 子分类视图
│   ├── tool_config_dialog.py # 工具配置对话框
│   └── image_selector.py    # 图片选择器
├── resources/            # 资源文件
│   ├── icons/           # 图标资源
│   └── styles/          # 样式文件
├── data/                 # 配置文件
│   ├── categories.json  # 分类配置
│   └── tools.json       # 工具配置
├── images/               # 图片资源
├── scripts/              # 辅助脚本
│   └── create_desktop_shortcut.py  # 快捷方式创建脚本
├── main.py               # 应用入口
├── requirements.txt      # 依赖列表
├── run_tool.vbs          # VBS启动脚本（隐藏终端）
├── run_tool.bat          # BAT启动脚本
├── image.ico             # 应用图标
└── README.md            # 项目文档
```

## ⚠️ 免责声明

1. 本工具仅供合法的渗透测试和安全评估使用
2. 使用本工具进行任何未授权的测试均属非法行为
3. 作者对使用本工具造成的任何后果不承担责任
4. 请在使用前遵守当地法律法规

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📞 交流

扫码添微入群，不止工具相磋，更有技术共研、闲叙吃瓜；方寸群聊间，既藏攻防干货，亦容烟火日常，盼与君共赴这场技术与烟火交织的相聚。

![交流群二维码](./images/README/image-20251128014833635.png)

---

**致每一位坚守攻防一线的红队蓝队战友：**

愿你的探针精准破局，盾牌坚不可摧；愿漏洞皆可预判，风险尽在掌控。以技术为刃，以安全为盾，在数字疆域护万家无虞，祝前路披荆斩棘，攻防皆胜，平安顺遂！

---

**项目地址：** [https://github.com/zifeiyu-sec/zifeiyuSec-Toolkit](https://github.com/zifeiyu-sec/zifeiyuSec-Toolkit)

**版本：** v1.0.1
**更新时间：** 2025-12-16