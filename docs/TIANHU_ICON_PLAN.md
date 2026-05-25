# 天狐 2.0 / 3.0 图标整理方案

当前资源概况：

- 图标文件：124 个
- 格式分布：`png` 66、`ico` 41、`svg` 13、`jpg` 3、`gif` 1
- 非 ASCII 文件名：3 个
- 重复 stem：`altoromutual`

命名约定：

1. `tool_vendor_product.ext` 用于本地工具图标
2. `domain_favicon.ext` 用于网站 / 站点类图标
3. `tianhu_import.svg` 作为天狐 3.0 导入兜底图标
4. `write-github.svg` / `black-github.png` / `github_1_1_1.svg` 保留为主题默认图标

天狐 2.0 / 3.0 导入时图标解析顺序：

1. 按工具名命中本地图标注册表
2. 按工具名对应的站点或官方主页下载 favicon
3. 按工具名称在线搜索，再下载搜索结果站点图标；单次导入限制通用搜索次数，避免导入被网络拖慢
4. 全部失败则回退到天狐 3.0 默认图标

当前已经优先整理的工具名：

- BurpSuit-Pro -> `burpsuite_1.png`
- FOFA / FOFA Viewer -> `fofa.info_favicon_1.ico`
- Nmap -> `nmap.png`
- Yakit -> `Yakit_icon.png`
- Proxifier / Proxifire -> `Proxifier_icon_1.png`
- Wireshark -> `wireshark.ico`
- CyberChef -> `CyberChef_icon.png`
- Amass -> `amass.png`
- Hunter / 鹰图 -> `hunter.qianxin.com_favicon_1.ico`
- Quake / 360Quake -> `quake.ico`
- Shodan -> `shodan.png`
- Censys -> `censys.ico`
- CTFHub -> `ctfhub.png`
- CTFShow -> `ctfshow.png`

后续新增图标时，优先补 `core/tianhu_icon_registry.py`，不要直接改导入流程。
