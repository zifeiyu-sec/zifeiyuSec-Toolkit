import json
import os
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from core.task_control import iter_response_chunks, raise_if_cancelled
from core.icon_validation import detect_icon_extension, is_probably_icon_data
from core.tool_metadata import (
    DOCUMENT_EXTENSIONS as TOOL_DOCUMENT_EXTENSIONS,
    TERMINAL_SOURCE_TYPES as TOOL_TERMINAL_SOURCE_TYPES,
    infer_import_tool_type_label,
)
from core.import_services import (
    CategoryMapper,
    ImportIconResolver,
    NativeConfigImporter,
    OfficialSyncService,
    TianhuImporter,
)
from core.tianhu_icon_registry import iter_tianhu_icon_names, iter_tianhu_icon_source_urls
from core.runtime_paths import (
    ensure_runtime_dir,
    get_bundle_path,
    get_runtime_path,
    looks_like_command_name,
    resolve_configured_path_value,
    resolve_icon_path_value,
)


class ToolConfigExchangeService:
    EXPORT_SCHEMA = "zifeiyu-toolkit-tools"
    EXPORT_VERSION = 2
    DEFAULT_ICON = "write-github.svg"
    TIANHU_IMPORT_TAG = "天狐导入"
    TIANHU_DEFAULT_ICON = "fox.ico"
    TIANHU3_DEFAULT_ICON = "tianhu_import.svg"
    TIANHU_SUPPORTED_VERSION = "2.0"
    TIANHU3_SUPPORTED_VERSION = "3.0"
    TIANHU_SUPPORTED_VERSIONS = {TIANHU_SUPPORTED_VERSION, TIANHU3_SUPPORTED_VERSION}
    TIANHU_ICON_EXTENSIONS = {".svg", ".png", ".ico", ".jpg", ".jpeg"}
    TIANHU_ICON_LIBRARY_DIR = "tianhu"
    TIANHU_ICON_LIBRARY_COMMON_DIR = "common"
    TIANHU_ICON_SEARCH_LIMIT = 24
    TIANHU_UNCLASSIFIED_SUBCATEGORY = "待分类（天狐导入）"
    TIANHU_DEFAULT_FALLBACK_CATEGORY = "开发与效率工具"
    TIANHU2_SHARED_CATEGORIES = {"最近启动", "我的收藏"}
    TIANHU2_SETTINGS_SIGNATURE_KEYS = {
        "python_path",
        "java8_path",
        "java11_path",
        "custom_interpreters",
        "favorite_tools",
        "recent_tools",
        "theme",
        "display_mode",
        "update_check",
    }

    WEB_TOOL_TYPES = {"网页"}
    TERMINAL_TOOL_TYPES = TOOL_TERMINAL_SOURCE_TYPES
    JAVA8_GUI_TYPE = "java8(图形化)"
    JAVA11_GUI_TYPE = "java11(图形化)"
    DOCUMENT_EXTENSIONS = TOOL_DOCUMENT_EXTENSIONS
    TIANHU2_SOURCE_CATEGORIES = {
        "webshell管理工具",
        "信息收集工具",
        "免杀工具",
        "其他工具",
        "后渗透工具",
        "抓包与代理工具",
        "框架漏洞利用工具",
        "漏洞扫描与利用工具",
        "爆破工具",
        "网页工具",
    }
    TIANHU3_SOURCE_CATEGORIES = TIANHU2_SOURCE_CATEGORIES | {"应急响应"}
    TIANHU2_REQUIRED_TOOL_FIELDS = {
        "name",
        "category",
        "type",
        "path",
        "params",
        "url",
    }
    TIANHU_CATEGORY_FALLBACK_RULES = {
        "webshell管理工具": ("Web 安全测试", "WebShell 管理"),
        "抓包与代理工具": ("Web 安全测试", "抓包与安全代理"),
        "信息收集工具": ("情报侦察与 OSINT", "综合信息收集"),
        "漏洞扫描与利用工具": ("漏洞扫描与利用", "综合漏洞扫描"),
        "框架漏洞利用工具": ("漏洞扫描与利用", "漏洞验证与 PoC"),
        "后渗透工具": ("内网与域安全", "内网信息收集"),
        "爆破工具": ("密码学与凭据", "在线与离线破解"),
        "免杀工具": ("内网与域安全", "免杀与对抗"),
        "应急响应": ("蓝队分析与应急响应", "应急响应"),
        "网页工具": ("靶场与资源导航", "导航站点"),
        "其他工具": ("开发与效率工具", "通用开发工具"),
    }
    TIANHU_ICON_ALIASES = [
        ("burp", "burpsuite_1.png"),
        ("goby", "Goby_icon.png"),
        ("nuclei", "Nuclei_GUI_icon_1.png"),
        ("nmap", "nmap.png"),
        ("yakit", "Yakit_icon.png"),
        ("proxifier", "Proxifier_icon_1.png"),
        ("wireshark", "wireshark.ico"),
        ("cyberchef", "CyberChef_icon.png"),
        ("amass", "amass.png"),
        ("fofa", "fofa.info_favicon_1.ico"),
        ("hunter", "hunter.qianxin.com_favicon_1.ico"),
        ("quake", "quake.ico"),
        ("shodan", "shodan.png"),
        ("censys", "censys.ico"),
        ("ctfhub", "ctfhub.png"),
        ("ctfshow", "ctfshow.png"),
        ("fox", "fox.ico"),
        ("tianhu", "tianhu_import.svg"),
    ]
    TIANHU_CATEGORY_MATCH_RULES = [
        (("webshell", "冰蝎", "哥斯拉", "蚁剑", "中国蚁剑", "behinder", "godzilla", "antsword", "alien", "cknife", "webshell管理"), ("Web 安全测试", "WebShell 管理")),
        (("burp", "mitmproxy", "fiddler", "proxifier", "charles", "wireshark", "http toolkit", "reqable", "yakit"), ("Web 安全测试", "抓包与安全代理")),
        (("frp", "gost", "nps", "clash", "v2ray", "xray", "chisel", "ligolo", "suo5"), ("内网与域安全", "代理与隧道")),
        (("sqlmap", "sql注入", "super sql", "ghauri", "bbqsql"), ("Web 安全测试", "注入类漏洞")),
        (("shiro", "fastjson", "jackson", "deserial", "ysoserial", "反序列化"), ("Web 安全测试", "反序列化与RCE")),
        (("fofa", "hunter", "quake", "zoomeye", "shodan", "censys", "criminalip", "fullhunt", "netlas", "daydaymap", "binaryedge", "threatbook"), ("情报侦察与 OSINT", "网络空间测绘")),
        (("oneforall", "subfinder", "amass", "ksubdomain", "subdomain"), ("情报侦察与 OSINT", "子域名与资产发现")),
        (("dirsearch", "gobuster", "feroxbuster", "dirbuster", "sensitive", "敏感文件"), ("情报侦察与 OSINT", "目录与敏感文件扫描")),
        (("whatweb", "ehole", "wappalyzer", "finger", "指纹", "webanalyzer"), ("情报侦察与 OSINT", "指纹识别")),
        (("whois", "备案", "icp"), ("情报侦察与 OSINT", "ICP备案与注册信息")),
        (("零零信安", "0.zone", "haveibeenpwned", "泄露", "暗网"), ("情报侦察与 OSINT", "社工与泄露情报")),
        (("blueteamtools", "蓝队分析辅助工具箱"), ("蓝队分析与应急响应", "蓝队综合工具")),
        (("应急响应", "应急", "响应", "取证", "日志", "蓝队", "edr", "forensics", "事件分析"), ("蓝队分析与应急响应", "应急响应")),
        (("企查查", "qcc", "爱企查", "aiqicha", "天眼查", "tianyancha", "七麦", "qimai", "小蓝本", "xiaolanben"), ("情报侦察与 OSINT", "企业与实名信息")),
        (("ip138", "chinaz", "站长工具", "site.ip138"), ("情报侦察与 OSINT", "在线网络探测")),
        (("cyberchef", "base64", "url编码", "编码", "解码", "decode", "encode", "jwt", "unicode"), ("密码学与凭据", "编码解码与数据处理")),
        (("decrypttools", "加密解密"), ("密码学与凭据", "加密解密工具")),
        (("hashcat", "john", "hydra", "medusa", "爆破", "brute", "crack"), ("密码学与凭据", "在线与离线破解")),
        (("md5", "sha1", "sha256", "hash", "ntlm"), ("密码学与凭据", "哈希识别与转换")),
        (("wordlist", "字典", "mask", "rules"), ("密码学与凭据", "字典生成与处理")),
        (("mimikatz", "lsassy", "sekurlsa", "dump", "凭据", "cookie"), ("密码学与凭据", "凭据提取")),
        (("bloodhound", "rubeus", "kerberos", "kerbrute", "adfind", "powerview", "ldap", "域", "域控", "adcs", "dcsync"), ("内网与域安全", "AD 图谱与攻击")),
        (("psexec", "wmiexec", "smbexec", "wmi", "横向", "lateral", "atexec"), ("内网与域安全", "横向移动")),
        (("cobalt", "beacon", "sliver", "quasar", "c2", "rat", "xiebro"), ("内网与域安全", "C2 与远控")),
        (("fscan", "kscan", "xscan", "masscan", "nmap", "rustscan", "portscan"), ("漏洞扫描与利用", "端口与服务扫描")),
        (("xray", "goby", "nuclei", "awvs", "nessus", "漏扫", "漏洞扫描"), ("漏洞扫描与利用", "综合漏洞扫描")),
        (("poc", "cve", "cnvd", "cnnvd", "nvd", "exploit", "exp", "seebug"), ("漏洞扫描与利用", "漏洞验证与 PoC")),
        (("cms", "cms漏洞", "oa漏洞", "web漏洞", "webscan", "scan4all", "泛微", "致远", "蓝凌", "通达", "用友", "weaver", "seeyon", "landray", "tongda", "yonyou"), ("漏洞扫描与利用", "Web 漏洞扫描")),
        (("potatotool", "potato", "redis-tools", "redis-rogue"), ("漏洞扫描与利用", "漏洞验证与 PoC")),
        (("httpx",), ("情报侦察与 OSINT", "综合信息收集")),
        (("hackthebox", "tryhackme", "vulnhub", "root-me", "ctfshow", "adworld", "ctf"), ("靶场与资源导航", "靶场与练习平台")),
        (("威胁情报", "virustotal", "threatbook", "sandbox", "沙箱", "habo", "peiqi", "avd.aliyun", "漏洞库", "文库", "bugbank"), ("靶场与资源导航", "漏洞库与情报库")),
        (("freebuf", "先知", "github", "wiki", "知识库", "secwiki", "gitee", "t00ls", "anquanke", "ichunqiu", "secpulse", "aqniu", "secrss", "doonsec", "cn-sec", "博客园", "csdn", "forum.butian", "forum.ywhack", "小迪渗透"), ("靶场与资源导航", "安全社区与论坛")),
        (("工具库", "导航", "云盘搜索", "lingfengyun", "tool.one-fox"), ("靶场与资源导航", "导航站点")),
        (("json", "yaml", "xml", "regex", "正则", "文本", "格式化", "beautify"), ("开发与效率工具", "正则与文本处理")),
        (("dnslog", "ceye", "callback.red", "httpcanary", "fiddler", "burp", "curl", "postman", "apifox", "apidog", "reqable", "httpie", "finalshell"), ("开发与效率工具", "网络调试")),
        (("api", "swagger", "graphql", "接口"), ("Web 安全测试", "API 接口测试")),
        (("auxtools", "everything"), ("开发与效率工具", "通用开发工具")),
        (("deepseekselftool", "deekseekselftools", "deepseek"), ("AI 安全与大模型", "Agent 与自动化")),
    ]
    REMOTE_JSON_TIMEOUT_SECONDS = 5
    REMOTE_JSON_CHUNK_SIZE = 64 * 1024

    def __init__(self, data_manager):
        self.data_manager = data_manager
        self._tianhu_icon_source_cache = {}
        self._tianhu_icon_online_search_count = 0
        self.category_mapper = CategoryMapper(self)
        self.import_icon_resolver = ImportIconResolver(self)
        self.native_importer = NativeConfigImporter(self)
        self.official_sync_service = OfficialSyncService(self)
        self.tianhu_importer = TianhuImporter(
            self,
            category_mapper=self.category_mapper,
            icon_resolver=self.import_icon_resolver,
        )

    def _export_sort_key(self, tool):
        return (
            self._to_int(tool.get("category_id"), 999999),
            self._to_int(tool.get("subcategory_id"), 999999),
            str(tool.get("name", "") or "").strip().casefold(),
            self._to_int(tool.get("id"), 999999),
        )

    def _build_export_tool(self, tool, category_map, subcategory_map):
        exported = {
            "name": str(tool.get("name", "") or "").strip(),
            "path": str(tool.get("path", "") or "").strip(),
            "description": str(tool.get("description", "") or "").strip(),
            "category_id": tool.get("category_id"),
            "subcategory_id": tool.get("subcategory_id"),
            "category_name": category_map.get(tool.get("category_id"), {}).get("name", ""),
            "subcategory_name": subcategory_map.get(tool.get("subcategory_id"), {}).get("name", ""),
            "background_image": str(tool.get("background_image", "") or "").strip(),
            "icon": str(tool.get("icon", self.DEFAULT_ICON) or self.DEFAULT_ICON).strip(),
            "is_favorite": self._to_bool(tool.get("is_favorite", False)),
            "arguments": str(tool.get("arguments", "") or "").strip(),
            "working_directory": str(tool.get("working_directory", "") or "").strip(),
            "run_in_terminal": self._to_bool(tool.get("run_in_terminal", False)),
            "is_web_tool": self._to_bool(tool.get("is_web_tool", False)),
            "type_label": str(tool.get("type_label", "") or "").strip(),
        }

        custom_interpreter_path = str(tool.get("custom_interpreter_path", "") or "").strip()
        custom_interpreter_type = str(tool.get("custom_interpreter_type", "") or "").strip().lower()
        if custom_interpreter_path:
            exported["custom_interpreter_path"] = custom_interpreter_path
        if custom_interpreter_type:
            exported["custom_interpreter_type"] = custom_interpreter_type

        sync_id = str(tool.get("sync_id", "") or "").strip()
        if sync_id:
            exported["sync_id"] = sync_id

        return exported

    def export_native_tools(self, file_path):
        """Export tools configuration (config only) to JSON file.
        Paths are kept as‑is. This is the original export used by the UI.
        """
        tools = list(self.data_manager.load_tools() or [])
        categories = list(self.data_manager.load_categories() or [])
        category_map, subcategory_map = self._build_category_maps(categories)

        exported_tools = [
            self._build_export_tool(tool, category_map, subcategory_map)
            for tool in sorted(tools, key=self._export_sort_key)
        ]

        payload = {
            "schema": self.EXPORT_SCHEMA,
            "version": self.EXPORT_VERSION,
            "source": "zifeiyu",
            "export_mode": "config_only",
            "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tool_count": len(exported_tools),
            "tools": exported_tools,
        }
        self._write_json(file_path, payload)
        return {
            "file_path": file_path,
            "exported": len(exported_tools),
            "mode": "config_only",
        }

    def import_native_tools(self, file_path):
        return self.native_importer.import_file(file_path).to_legacy_result()

    def _import_native_tools_legacy(self, file_path):
        payload = self._read_json(file_path)
        if isinstance(payload, dict):
            payload_source = str(payload.get("source", "") or "").strip().lower()
            payload_schema = str(payload.get("schema", "") or "").strip()
            if payload_source == "tianhu":
                raise ValueError("检测到天狐导出文件，请使用“导入天狐2.0”功能。")
            if payload_schema and payload_schema != self.EXPORT_SCHEMA:
                raise ValueError(f"不支持的配置文件 schema: {payload_schema}")

        tools_payload = self._extract_native_tools_payload(payload)
        categories = list(self.data_manager.load_categories() or [])

        existing_tools = list(self.data_manager.load_tools() or [])
        next_id = self._next_tool_id(existing_tools)
        seen_fingerprints = {self._tool_fingerprint(tool) for tool in existing_tools}

        imported_tools = []
        skipped = 0
        for item in tools_payload:
            normalized = self._normalize_native_tool(item, categories)
            fingerprint = self._tool_fingerprint(normalized)
            if fingerprint in seen_fingerprints:
                skipped += 1
                continue

            normalized["id"] = next_id
            next_id += 1
            imported_tools.append(normalized)
            seen_fingerprints.add(fingerprint)

        if imported_tools:
            existing_tools.extend(imported_tools)
            if not self.data_manager.save_tools(existing_tools):
                raise OSError("导入原生工具配置失败，保存工具配置未成功。")

        return {
            "imported": len(imported_tools),
            "skipped": skipped,
            "total": len(tools_payload),
        }

    def _report_progress(self, progress_callback, message):
        if callable(progress_callback):
            try:
                progress_callback(str(message or "").strip())
            except Exception:
                return

    def sync_official_tools_from_url(self, source_url, update_existing=True, cancel_requested=None, progress_callback=None):
        return self.official_sync_service.sync_from_url(
            source_url,
            update_existing=update_existing,
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        ).to_legacy_result()

    def _sync_official_tools_from_url_legacy(self, source_url, update_existing=True, cancel_requested=None, progress_callback=None):
        url_text = str(source_url or "").strip()
        if not url_text:
            raise ValueError("未配置官方工具库地址。")
        if not (url_text.startswith("http://") or url_text.startswith("https://")):
            raise ValueError("官方工具库地址必须为 http/https 链接。")

        raise_if_cancelled(cancel_requested, "已取消同步官方工具库。")
        self._report_progress(progress_callback, "正在下载官方工具库...")
        payload = self._fetch_remote_json(
            url_text,
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )
        if isinstance(payload, dict):
            payload_schema = str(payload.get("schema", "") or "").strip()
            if payload_schema and payload_schema != self.EXPORT_SCHEMA:
                raise ValueError(f"不支持的官方工具库 schema: {payload_schema}")

        raise_if_cancelled(cancel_requested, "已取消同步官方工具库。")
        self._report_progress(progress_callback, "正在整理官方工具数据...")
        tools_payload = self._extract_native_tools_payload(payload)
        categories = list(self.data_manager.load_categories() or [])
        existing_tools = list(self.data_manager.load_tools() or [])
        backup_path = self._backup_tools_snapshot(existing_tools, url_text)
        next_id = self._next_tool_id(existing_tools)
        should_update = self._to_bool(update_existing)

        sync_key_index = {}
        fingerprint_index = {}
        for index, tool in enumerate(existing_tools):
            sync_key = self._sync_key(tool.get("sync_id"))
            if sync_key:
                sync_key_index[sync_key] = index
            fingerprint_index[self._tool_fingerprint(tool)] = index

        imported = 0
        updated = 0
        skipped = 0
        total_tools = len(tools_payload)
        for index, item in enumerate(tools_payload, start=1):
            raise_if_cancelled(cancel_requested, "已取消同步官方工具库。")
            if index == 1 or index == total_tools or index % 25 == 0:
                self._report_progress(progress_callback, f"正在合并官方工具库... {index}/{total_tools}")
            normalized = self._normalize_native_tool(item, categories)
            sync_id = str(item.get("sync_id", "") or normalized.get("sync_id", "")).strip()
            sync_key = self._sync_key(sync_id)
            if sync_id:
                normalized["sync_id"] = sync_id

            match_index = None
            if sync_key and sync_key in sync_key_index:
                match_index = sync_key_index[sync_key]
            else:
                match_index = fingerprint_index.get(self._tool_fingerprint(normalized))

            if match_index is None:
                normalized["id"] = next_id
                next_id += 1
                normalized["sync_source"] = "official"
                existing_tools.append(normalized)
                new_index = len(existing_tools) - 1
                if sync_key:
                    sync_key_index[sync_key] = new_index
                fingerprint_index[self._tool_fingerprint(normalized)] = new_index
                imported += 1
                continue

            if not should_update:
                skipped += 1
                continue

            existing_tool = existing_tools[match_index]
            merged = self._merge_official_tool(existing_tool, normalized, sync_id)
            existing_tools[match_index] = merged
            if sync_key:
                sync_key_index[sync_key] = match_index
            fingerprint_index[self._tool_fingerprint(merged)] = match_index
            updated += 1

        if imported or updated:
            raise_if_cancelled(cancel_requested, "已取消同步官方工具库。")
            self._report_progress(progress_callback, "正在保存同步结果...")
            if not self.data_manager.save_tools(existing_tools):
                raise OSError("同步官方工具库失败，保存工具配置未成功。")

        return {
            "source_url": url_text,
            "total": len(tools_payload),
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "backup_path": backup_path,
            "update_existing": should_update,
        }

    def import_tianhu_tools(
        self,
        source_path,
        cancel_requested=None,
        progress_callback=None,
        download_missing_icons=False,
    ):
        return self.tianhu_importer.import_file(
            source_path,
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
            download_missing_icons=download_missing_icons,
        ).to_legacy_result()

    def _import_tianhu_tools_legacy(
        self,
        source_path,
        cancel_requested=None,
        progress_callback=None,
        download_missing_icons=False,
    ):
        self._report_progress(progress_callback, "正在读取天狐配置...")
        raise_if_cancelled(cancel_requested, "已取消导入天狐工具。")
        self._tianhu_icon_online_search_count = 0
        tools_payload, settings, source_root, detected_version = self._load_tianhu_payload(source_path)
        categories = list(self.data_manager.load_categories() or [])

        existing_tools = list(self.data_manager.load_tools() or [])
        next_id = self._next_tool_id(existing_tools)
        seen_fingerprints = {self._tool_fingerprint(tool) for tool in existing_tools}

        imported_tools = []
        skipped = 0
        category_stats = {}
        categories_changed = False

        total_tools = len(tools_payload)
        for index, raw_tool in enumerate(tools_payload, start=1):
            raise_if_cancelled(cancel_requested, "已取消导入天狐工具。")
            if index == 1 or index == total_tools or index % 25 == 0:
                self._report_progress(progress_callback, f"正在导入天狐工具... {index}/{total_tools}")
            normalized = self._convert_tianhu_tool(
                raw_tool,
                source_root,
                settings,
                categories,
                detected_version,
                download_missing_icons=download_missing_icons,
            )
            fingerprint = self._tool_fingerprint(normalized)
            if fingerprint in seen_fingerprints:
                skipped += 1
                continue

            categories_changed = self._ensure_tianhu_tool_subcategory(categories, normalized) or categories_changed

            normalized["id"] = next_id
            next_id += 1
            imported_tools.append(normalized)
            seen_fingerprints.add(fingerprint)

            category_name = normalized.get("_resolved_category_name", "") or normalized.get("_mapped_category_name", "")
            if category_name:
                category_stats[category_name] = category_stats.get(category_name, 0) + 1

        if imported_tools:
            if categories_changed and not self.data_manager.save_categories(categories):
                raise OSError("保存天狐导入创建的临时子分类失败。")

            for tool in imported_tools:
                tool.pop("_mapped_category_name", None)
                tool.pop("_mapped_subcategory_name", None)
                tool.pop("_resolved_category_name", None)
                tool.pop("_resolved_subcategory_name", None)
            existing_tools.extend(imported_tools)
            self._report_progress(progress_callback, "正在保存天狐导入结果...")
            if not self.data_manager.save_tools(existing_tools):
                raise OSError("导入天狐工具失败，保存工具配置未成功。")

        return {
            "imported": len(imported_tools),
            "skipped": skipped,
            "total": len(tools_payload),
            "category_stats": category_stats,
            "source_path": source_path,
            "detected_version": detected_version,
            "created_placeholder_subcategory": categories_changed,
        }

    def get_tianhu_tools(self):
        tools = list(self.data_manager.load_tools() or [])
        return [tool for tool in tools if self._is_tianhu_tool(tool)]

    def remove_tianhu_tools(self):
        existing_tools = list(self.data_manager.load_tools() or [])
        removed_tools = [tool for tool in existing_tools if self._is_tianhu_tool(tool)]
        if not removed_tools:
            return {
                "removed": 0,
                "remaining": len(existing_tools),
                "removed_names": [],
            }

        remaining_tools = [tool for tool in existing_tools if not self._is_tianhu_tool(tool)]
        if not self.data_manager.save_tools(remaining_tools):
            raise OSError("删除天狐导入工具失败，保存工具配置未成功。")

        return {
            "removed": len(removed_tools),
            "remaining": len(remaining_tools),
            "removed_names": [
                str(tool.get("name", "") or "").strip()
                for tool in removed_tools
                if str(tool.get("name", "") or "").strip()
            ],
        }

    def _extract_native_tools_payload(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("tools"), list):
            return payload.get("tools") or []
        raise ValueError("配置文件格式不正确，未找到可导入的工具列表。")

    def _normalize_native_tool(self, item, categories):
        tool = dict(item or {})
        tool.pop("id", None)

        category_name = str(tool.pop("category_name", "") or "").strip()
        subcategory_name = str(tool.pop("subcategory_name", "") or "").strip()

        category_id = tool.get("category_id")
        subcategory_id = tool.get("subcategory_id")
        if category_name:
            resolved_category_id, resolved_subcategory_id, _, _ = self._resolve_category_assignment(
                categories,
                category_name,
                subcategory_name,
            )
            if resolved_category_id is not None:
                category_id = resolved_category_id
                subcategory_id = resolved_subcategory_id
        else:
            category_id, subcategory_id = self._sanitize_category_assignment(
                categories,
                category_id,
                subcategory_id,
            )

        normalized_tool = {
            "name": str(tool.get("name", "") or "").strip(),
            "path": str(tool.get("path", "") or "").strip(),
            "description": str(tool.get("description", "") or "").strip(),
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "background_image": str(tool.get("background_image", "") or "").strip(),
            "icon": str(tool.get("icon", self.DEFAULT_ICON) or self.DEFAULT_ICON).strip(),
            "is_favorite": self._to_bool(tool.get("is_favorite", False)),
            "arguments": str(tool.get("arguments", "") or "").strip(),
            "working_directory": str(tool.get("working_directory", "") or "").strip(),
            "run_in_terminal": self._to_bool(tool.get("run_in_terminal", False)),
            "is_web_tool": self._to_bool(tool.get("is_web_tool", False)),
            "type_label": str(tool.get("type_label", "") or "").strip(),
            "usage_count": 0,
            "last_used": None,
        }

        custom_interpreter_path = str(tool.get("custom_interpreter_path", "") or "").strip()
        custom_interpreter_type = str(tool.get("custom_interpreter_type", "") or "").strip().lower()
        if custom_interpreter_path:
            normalized_tool["custom_interpreter_path"] = custom_interpreter_path
        if custom_interpreter_type:
            normalized_tool["custom_interpreter_type"] = custom_interpreter_type

        sync_id = str(tool.get("sync_id", "") or "").strip()
        if sync_id:
            normalized_tool["sync_id"] = sync_id

        return normalized_tool

    def _load_tianhu_payload(self, source_path):
        source_text = str(source_path or "").strip()
        if not source_text:
            raise ValueError("未提供天狐配置路径。")

        normalized_source = os.path.abspath(source_text)
        if os.path.isfile(normalized_source):
            payload = self._read_json(normalized_source)
            tools_payload = self._extract_tianhu_tools_payload(payload)
            settings = payload.get("settings") if isinstance(payload, dict) else {}
            if not isinstance(settings, dict):
                settings = {}
            source_root = self._guess_tianhu_root(payload, tools_payload)
            detected_version = self._detect_tianhu_version(payload, tools_payload)
            if detected_version not in self.TIANHU_SUPPORTED_VERSIONS:
                raise ValueError("当前仅支持导入天狐 2.0 / 3.0 导出配置，请确认导出文件来自天狐工具箱。")
            return tools_payload, settings, source_root, detected_version

        if os.path.isdir(normalized_source):
            tools_file = os.path.join(normalized_source, "config", "tools.json")
            settings_file = os.path.join(normalized_source, "config", "settings.json")
            tools_payload = self._extract_tianhu_tools_payload(self._read_json(tools_file))
            settings = {}
            if os.path.exists(settings_file):
                raw_settings = self._read_json(settings_file)
                if isinstance(raw_settings, dict):
                    settings = raw_settings
            payload = {"tools": tools_payload, "settings": settings}
            detected_version = self._detect_tianhu_version(payload, tools_payload)
            if detected_version not in self.TIANHU_SUPPORTED_VERSIONS:
                raise ValueError("当前仅支持导入天狐 2.0 / 3.0 导出配置，请确认目录来自天狐工具箱。")
            return tools_payload, settings, normalized_source, detected_version

        raise FileNotFoundError(f"天狐配置不存在: {source_text}")

    def _detect_tianhu_version(self, payload, tools_payload):
        if not tools_payload or not isinstance(tools_payload, list):
            return ""

        valid_tools = [
            item for item in tools_payload
            if isinstance(item, dict) and self.TIANHU2_REQUIRED_TOOL_FIELDS.issubset(item.keys())
        ]
        if not valid_tools or len(valid_tools) != len(tools_payload):
            return ""

        if isinstance(payload, list):
            return self.TIANHU3_SUPPORTED_VERSION

        if not isinstance(payload, dict):
            return ""

        categories = payload.get("categories")
        settings = payload.get("settings")
        if categories is not None and not isinstance(categories, list):
            return ""
        if settings is not None and not isinstance(settings, dict):
            return ""

        normalized_categories = {
            str(item or "").strip().casefold()
            for item in (categories or [])
            if str(item or "").strip()
        }
        normalized_tool_categories = {
            str(item.get("category", "") or "").strip().casefold()
            for item in valid_tools
            if str(item.get("category", "") or "").strip()
        }
        normalized_source_categories = {item.casefold() for item in self.TIANHU2_SOURCE_CATEGORIES}
        normalized_shared_categories = {item.casefold() for item in self.TIANHU2_SHARED_CATEGORIES}
        signature_key_count = sum(
            1
            for key in self.TIANHU2_SETTINGS_SIGNATURE_KEYS
            if isinstance(settings, dict) and key in settings
        )

        if normalized_categories & normalized_source_categories:
            return self.TIANHU_SUPPORTED_VERSION
        if normalized_tool_categories & normalized_source_categories:
            return self.TIANHU_SUPPORTED_VERSION
        if normalized_categories & normalized_shared_categories and signature_key_count >= 2:
            return self.TIANHU_SUPPORTED_VERSION
        if signature_key_count >= 4:
            return self.TIANHU_SUPPORTED_VERSION
        normalized_tianhu3_categories = {item.casefold() for item in self.TIANHU3_SOURCE_CATEGORIES}
        if normalized_categories & normalized_tianhu3_categories:
            return self.TIANHU3_SUPPORTED_VERSION
        if normalized_tool_categories & normalized_tianhu3_categories:
            return self.TIANHU3_SUPPORTED_VERSION

        return ""

    def _extract_tianhu_tools_payload(self, payload):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("tools"), list):
            return payload.get("tools") or []
        raise ValueError("天狐导出文件格式不正确，未找到 tools 列表。")

    def _guess_tianhu_root(self, payload, tools_payload):
        if isinstance(payload, dict):
            settings = payload.get("settings") or {}
            if isinstance(settings, dict):
                for key in ("python_path", "java8_path", "java11_path"):
                    value = settings.get(key)
                    root = self._extract_tianhu_root_from_path(value)
                    if root:
                        return root

        for raw_tool in tools_payload or []:
            root = self._extract_tianhu_root_from_path(raw_tool.get("path"))
            if root:
                return root
        return ""

    def _extract_tianhu_root_from_path(self, value):
        text = str(value or "").strip()
        if not text:
            return ""

        normalized = os.path.normpath(text)
        parts = normalized.split(os.sep)
        for index, part in enumerate(parts):
            if part.casefold() == "th2":
                return os.sep.join(parts[: index + 1])
        return ""

    def _convert_tianhu_tool(
        self,
        raw_tool,
        tianhu_root,
        settings,
        categories,
        detected_version,
        download_missing_icons=False,
    ):
        name = str(raw_tool.get("name", "") or "").strip()
        source_category = str(raw_tool.get("category", "") or "").strip()
        source_type = str(raw_tool.get("type", "") or "").strip()
        description = str(raw_tool.get("description", "") or "").strip()
        raw_path = str(raw_tool.get("path", "") or "").strip()
        raw_url = str(raw_tool.get("url", "") or "").strip()
        params = str(raw_tool.get("params", "") or "").strip()
        source_group = str(raw_tool.get("group", "") or "").strip()

        is_web_tool = self._is_tianhu_web_tool(source_type, raw_url, raw_path)
        final_path = raw_url if is_web_tool else self._resolve_tianhu_path(tianhu_root, raw_path)
        working_directory = ""
        if not is_web_tool and final_path:
            working_directory = self._derive_working_directory(final_path)

        mapped_category_name, mapped_subcategory_name = self._map_tianhu_category(raw_tool)
        category_id, subcategory_id, resolved_category_name, resolved_subcategory_name = (
            self._resolve_category_assignment(categories, mapped_category_name, mapped_subcategory_name)
        )

        tool = {
            "name": name,
            "path": final_path,
            "description": description,
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "background_image": "",
            "icon": self._resolve_tianhu_icon(
                raw_tool,
                final_path,
                is_web_tool,
                detected_version,
                allow_online_lookup=download_missing_icons,
            ),
            "is_favorite": False,
            "arguments": params,
            "working_directory": working_directory,
            "run_in_terminal": self._should_run_in_terminal(source_type, final_path),
            "is_web_tool": is_web_tool,
            "type_label": self._infer_type_label(final_path, source_type, is_web_tool),
            "usage_count": 0,
            "last_used": None,
            "import_source": "tianhu",
            "import_source_version": detected_version,
            "import_source_root": tianhu_root,
            "source_category": source_category,
            "source_type": source_type,
            "source_group": source_group,
            "_mapped_category_name": mapped_category_name,
            "_mapped_subcategory_name": mapped_subcategory_name,
            "_resolved_category_name": resolved_category_name,
            "_resolved_subcategory_name": resolved_subcategory_name,
        }

        self._apply_tianhu_interpreter(tool, raw_tool, settings, tianhu_root)
        return tool

    def _resolve_tianhu_icon(self, raw_tool, final_path, is_web_tool, detected_version, allow_online_lookup=False):
        icon_name = self._find_tianhu_library_icon(raw_tool, final_path, is_web_tool, detected_version)
        if icon_name:
            return icon_name

        icon_name = self._find_tianhu_existing_icon(raw_tool, final_path, is_web_tool)
        if icon_name:
            return icon_name

        if not allow_online_lookup:
            return self._resolve_tianhu_default_icon(detected_version)

        downloaded_icon = self._download_tianhu_tool_icon(raw_tool, is_web_tool)
        if downloaded_icon:
            return downloaded_icon

        return self._resolve_tianhu_default_icon(detected_version)

    def _resolve_tianhu_default_icon(self, detected_version):
        candidates = []
        if str(detected_version or "").strip() == self.TIANHU3_SUPPORTED_VERSION:
            candidates.append(self.TIANHU3_DEFAULT_ICON)
        candidates.extend([self.TIANHU_DEFAULT_ICON, self.DEFAULT_ICON])

        for candidate in candidates:
            resolved = resolve_icon_path_value(candidate)
            if resolved:
                return os.fspath(resolved.name)

        return candidates[0]

    def _find_tianhu_existing_icon(self, raw_tool, final_path, is_web_tool):
        seen = set()
        for candidate in self._build_tianhu_icon_candidates(raw_tool, final_path, is_web_tool):
            normalized = str(candidate or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            resolved = resolve_icon_path_value(normalized)
            if resolved and resolved.suffix.casefold() in self.TIANHU_ICON_EXTENSIONS:
                return self._format_icon_value(resolved)
        return ""

    def _find_tianhu_library_icon(self, raw_tool, final_path, is_web_tool, detected_version):
        seen = set()
        for key in self._build_tianhu_icon_library_keys(raw_tool, final_path, is_web_tool):
            for candidate in self._build_tianhu_icon_library_candidates(key, detected_version):
                if candidate in seen:
                    continue
                seen.add(candidate)
                resolved = resolve_icon_path_value(candidate)
                if resolved and resolved.suffix.casefold() in self.TIANHU_ICON_EXTENSIONS:
                    return self._format_icon_value(resolved)
        return ""

    def _build_tianhu_icon_library_candidates(self, key, detected_version):
        normalized_key = self._normalize_tianhu_icon_key(key)
        if not normalized_key:
            return []

        version = str(detected_version or "").strip()
        library_roots = []
        if version in self.TIANHU_SUPPORTED_VERSIONS:
            library_roots.append((self.TIANHU_ICON_LIBRARY_DIR, version))
        library_roots.append((self.TIANHU_ICON_LIBRARY_DIR, self.TIANHU_ICON_LIBRARY_COMMON_DIR))

        candidates = []
        for root_parts in library_roots:
            candidates.append("/".join((*root_parts, normalized_key)))
        return candidates

    def _build_tianhu_icon_library_keys(self, raw_tool, final_path, is_web_tool):
        seen = set()

        if isinstance(raw_tool, dict):
            for field_name in ("name", "path", "url", "description", "group"):
                value = raw_tool.get(field_name, "")
                for key in self._expand_tianhu_icon_key(value):
                    if key and key not in seen:
                        seen.add(key)
                        yield key

            tags = raw_tool.get("tags", [])
            if isinstance(tags, (list, tuple, set)):
                tag_values = tags
            else:
                tag_values = [tags]
            for tag in tag_values:
                for key in self._expand_tianhu_icon_key(tag):
                    if key and key not in seen:
                        seen.add(key)
                        yield key

        for value in self._build_tianhu_icon_candidates(raw_tool, final_path, is_web_tool):
            for key in self._expand_tianhu_icon_key(value):
                if key and key not in seen:
                    seen.add(key)
                    yield key

    def _expand_tianhu_icon_key(self, value):
        text = str(value or "").strip()
        if not text:
            return []

        keys = []
        basename = os.path.basename(text.replace("\\", "/"))
        stem = os.path.splitext(basename)[0] if basename else text
        for item in (text, basename, stem):
            normalized = self._normalize_tianhu_icon_key(item)
            if normalized:
                keys.append(normalized)

        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9._+-]{1,}", text):
            normalized = self._normalize_tianhu_icon_key(token)
            if normalized:
                keys.append(normalized)

        return keys

    def _normalize_tianhu_icon_key(self, value):
        text = unquote(str(value or "").strip()).casefold()
        if not text:
            return ""

        text = os.path.basename(text.replace("\\", "/"))
        text = os.path.splitext(text)[0]
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")

    def _format_icon_value(self, resolved):
        resolved_text = os.path.abspath(os.fspath(resolved))
        for root in (
            get_runtime_path("resources", "icons"),
            get_bundle_path("resources", "icons"),
        ):
            root_text = os.path.abspath(os.fspath(root))
            try:
                common_path = os.path.commonpath([resolved_text, root_text])
            except ValueError:
                continue
            if common_path == root_text:
                return os.path.relpath(resolved_text, root_text).replace(os.sep, "/")
        return os.fspath(resolved.name)

    def _build_tianhu_icon_candidates(self, raw_tool, final_path, is_web_tool):
        search_text = self._build_tianhu_keyword_text(raw_tool)
        candidates = []

        for icon_name in iter_tianhu_icon_names(raw_tool):
            candidates.append(icon_name)

        raw_path = str(raw_tool.get("path", "") or "").strip()
        path_name = os.path.basename(str(final_path or "").strip()) if final_path else ""
        path_stem = os.path.splitext(path_name)[0] if path_name else ""
        for value in (path_name, path_stem, raw_path, os.path.basename(raw_path)):
            text = str(value or "").strip()
            if text:
                candidates.append(text)

        if is_web_tool:
            candidates.extend(self._build_tianhu_web_icon_candidates(raw_tool.get("url", "")))

        for keyword, icon_name in self.TIANHU_ICON_ALIASES:
            if keyword and keyword in search_text:
                candidates.append(icon_name)

        return candidates

    def _download_tianhu_tool_icon(self, raw_tool, is_web_tool):
        if bool(is_web_tool):
            downloaded_icon = self._download_tianhu_web_icon(raw_tool.get("url", ""))
            if downloaded_icon:
                return downloaded_icon

        for source_url in iter_tianhu_icon_source_urls(raw_tool):
            downloaded_icon = self._download_tianhu_web_icon(source_url)
            if downloaded_icon:
                return downloaded_icon

        tool_name = str(raw_tool.get("name", "") or "").strip()
        if not tool_name:
            return ""

        cache_key = tool_name.casefold()
        if cache_key in self._tianhu_icon_source_cache:
            search_url = self._tianhu_icon_source_cache[cache_key]
        else:
            if self._tianhu_icon_online_search_count >= self.TIANHU_ICON_SEARCH_LIMIT:
                return ""
            self._tianhu_icon_online_search_count += 1
            search_url = self._search_tianhu_icon_source_url(tool_name)
            self._tianhu_icon_source_cache[cache_key] = search_url

        if search_url:
            downloaded_icon = self._download_tianhu_web_icon(search_url)
            if downloaded_icon:
                return downloaded_icon

        return ""

    def _build_tianhu_web_icon_candidates(self, url):
        text = str(url or "").strip()
        if not text:
            return []

        try:
            parsed = urlparse(text)
        except Exception:
            return []

        domain = str(parsed.netloc or "").strip().casefold()
        if not domain:
            return []

        candidates = [
            f"{domain}_favicon_1.ico",
            f"{domain}_favicon.ico",
            f"{domain}.ico",
            f"{domain}.png",
        ]
        last_label = domain.split(".")[0]
        if last_label and last_label != domain:
            candidates.extend([
                f"{last_label}.ico",
                f"{last_label}.png",
            ])
        return candidates

    def _download_tianhu_web_icon(self, url, timeout=4.0, icon_dir=None, target_name=None):
        text = str(url or "").strip()
        if not text:
            return ""

        try:
            parsed = urlparse(text)
        except Exception:
            return ""

        if not parsed.scheme or not parsed.netloc:
            return ""

        domain = parsed.netloc.strip()
        base = f"{parsed.scheme}://{domain}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        }
        if icon_dir is None:
            icon_dir = ensure_runtime_dir("resources", "icons")
        else:
            icon_dir = os.fspath(icon_dir)
            os.makedirs(icon_dir, exist_ok=True)

        for candidate in (
            f"{base}/favicon.ico",
            f"{base}/favicon.png",
            f"{base}/favicon.svg",
            f"{base}/apple-touch-icon.png",
            f"https://{domain}/favicon.ico",
            f"http://{domain}/favicon.ico",
        ):
            downloaded = self._download_tianhu_icon_candidate(
                candidate,
                domain,
                headers,
                timeout,
                icon_dir,
                target_name=target_name,
            )
            if downloaded:
                return downloaded
        return ""

    def _search_tianhu_icon_source_url(self, tool_name, timeout=4.0):
        text = str(tool_name or "").strip()
        if not text:
            return ""

        search_url = f"https://duckduckgo.com/html/?q={quote_plus(text + ' official site icon')}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        }

        try:
            request = Request(search_url, headers=headers)
            with urlopen(request, timeout=timeout) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except (HTTPError, URLError, OSError, ValueError):
            return ""

        for candidate in self._extract_tianhu_search_result_urls(html):
            if candidate:
                return candidate
        return ""

    def _extract_tianhu_search_result_urls(self, html):
        if not html:
            return []

        candidates = []
        patterns = [
            r'href="[^"]*uddg=([^"&]+)',
            r'href="(https?://[^"]+)"',
        ]
        for pattern in patterns:
            for match in re.findall(pattern, html, flags=re.IGNORECASE):
                candidate = unquote(match).strip()
                if not candidate:
                    continue
                if candidate.startswith("//"):
                    candidate = "https:" + candidate
                if candidate.startswith(("http://", "https://")) and "duckduckgo.com" not in candidate.casefold():
                    candidates.append(candidate)
        seen = set()
        ordered = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            ordered.append(candidate)
        return ordered

    def _download_tianhu_icon_candidate(self, candidate, domain, headers, timeout, icon_dir, target_name=None):
        try:
            req = Request(candidate, headers=headers)
            with urlopen(req, timeout=timeout) as response:
                data = response.read()
                if not data or len(data) < 10:
                    return ""

                content_type = (response.headers.get("Content-Type", "") or "").lower()
                if not is_probably_icon_data(data, source_url=candidate, content_type=content_type):
                    return ""
                ext = self._detect_icon_extension(candidate, content_type, data=data)
                filename = self._save_tianhu_icon_file(icon_dir, domain, ext, data, target_name=target_name)
                if filename:
                    return filename
        except Exception:
            return ""
        return ""

    def _detect_icon_extension(self, source_url, content_type, data=b""):
        return detect_icon_extension(source_url=source_url, content_type=content_type, data=data)

    def _save_tianhu_icon_file(self, icon_dir, domain, ext, data, target_name=None):
        safe_domain = str(domain or "").replace(":", "_").replace("/", "_")
        base_name = str(target_name or "").strip()
        if base_name:
            safe_base = re.sub(r"[^A-Za-z0-9._-]+", "_", base_name).strip("._-") or safe_domain
            filename = f"{safe_base}{ext}"
        else:
            filename = f"{safe_domain}_favicon{ext}"
        path = os.path.join(os.fspath(icon_dir), filename)

        counter = 1
        while os.path.exists(path):
            if base_name:
                filename = f"{safe_base}_{counter}{ext}"
            else:
                filename = f"{safe_domain}_favicon_{counter}{ext}"
            path = os.path.join(os.fspath(icon_dir), filename)
            counter += 1

        try:
            with open(path, "wb") as file_handle:
                file_handle.write(data)
            return filename
        except Exception:
            return ""

    def _is_tianhu_web_tool(self, source_type, raw_url, raw_path):
        source_type_normalized = str(source_type or "").strip().casefold()
        url_text = str(raw_url or "").strip()
        path_text = str(raw_path or "").strip()
        if url_text.startswith(("http://", "https://")):
            return True
        if source_type_normalized in {item.casefold() for item in self.WEB_TOOL_TYPES}:
            return True
        return path_text.startswith(("http://", "https://"))

    def _apply_tianhu_interpreter(self, tool, raw_tool, settings, tianhu_root):
        source_type = str(raw_tool.get("type", "") or "").strip()
        source_type_key = source_type.casefold()
        custom_name = str(raw_tool.get("custom_interpreter_name", "") or "").strip()
        custom_type = str(raw_tool.get("custom_interpreter_type", "") or "").strip().lower()

        interpreter_path = ""
        interpreter_type = ""

        if source_type_key == "python":
            interpreter_type = "python"
            interpreter_path = self._resolve_tianhu_path(tianhu_root, settings.get("python_path", ""))
        elif source_type_key == self.JAVA8_GUI_TYPE:
            interpreter_type = "java"
            interpreter_path = self._resolve_java_interpreter(
                self._resolve_tianhu_path(tianhu_root, settings.get("java8_path", "")),
                console=tool.get("run_in_terminal", False),
            )
        elif source_type_key == self.JAVA11_GUI_TYPE:
            interpreter_type = "java"
            interpreter_path = self._resolve_java_interpreter(
                self._resolve_tianhu_path(tianhu_root, settings.get("java11_path", "")),
                console=tool.get("run_in_terminal", False),
            )

        if custom_name and custom_type:
            custom_path = self._resolve_custom_interpreter(settings, custom_name, custom_type, tianhu_root)
            if custom_path:
                interpreter_type = custom_type
                if custom_type == "java":
                    custom_path = self._resolve_java_interpreter(
                        custom_path,
                        console=tool.get("run_in_terminal", False),
                    )
                interpreter_path = custom_path

        if interpreter_path:
            tool["custom_interpreter_path"] = interpreter_path
        if interpreter_type:
            tool["custom_interpreter_type"] = interpreter_type

    def _resolve_custom_interpreter(self, settings, custom_name, custom_type, tianhu_root):
        for item in settings.get("custom_interpreters", []) or []:
            if str(item.get("name", "") or "").strip() != custom_name:
                continue
            if str(item.get("type", "") or "").strip().lower() != custom_type:
                continue
            return self._resolve_tianhu_path(tianhu_root, item.get("path", ""))
        return ""

    def _resolve_java_interpreter(self, base_path, console=False):
        if not base_path:
            return ""
        candidate = os.path.abspath(base_path)
        if os.path.isdir(candidate):
            preferred_name = "java.exe" if console else "javaw.exe"
            preferred_path = os.path.join(candidate, preferred_name)
            fallback_path = os.path.join(candidate, "java.exe")
            if os.path.exists(preferred_path):
                return preferred_path
            if os.path.exists(fallback_path):
                return fallback_path
        return candidate

    def _resolve_tianhu_path(self, tianhu_root, raw_path):
        text = str(raw_path or "").strip()
        if not text:
            return ""
        if text.startswith(("http://", "https://")):
            return text

        normalized = text.replace("/", os.sep).replace("\\", os.sep)
        if os.path.isabs(normalized):
            if not tianhu_root and normalized.startswith((os.sep, "\\", "/")):
                normalized = normalized.lstrip("\\/")
                return os.path.normpath(normalized)
            return os.path.normpath(normalized)

        if tianhu_root:
            normalized = normalized.lstrip("\\/")
            return os.path.normpath(os.path.join(tianhu_root, normalized))
        return os.path.normpath(normalized)

    def _derive_working_directory(self, path):
        text = str(path or "").strip()
        if not text:
            return ""
        if looks_like_command_name(text):
            return ""

        base_dir = getattr(self.data_manager, "config_dir", None)
        try:
            resolved_path = resolve_configured_path_value(
                text,
                base_dir=base_dir,
                allow_command_name=True,
            )
        except (OSError, ValueError):
            resolved_path = None

        if resolved_path is None:
            return ""

        resolved_text = os.fspath(resolved_path)
        if os.path.isdir(resolved_text) or self._path_looks_like_directory(text):
            return resolved_text
        return os.path.dirname(resolved_text) or resolved_text

    def _path_looks_like_directory(self, path):
        text = str(path or "").strip()
        if not text:
            return False
        if text.endswith(("/", "\\")):
            return True
        return not os.path.splitext(os.path.basename(text))[1]

    def _should_run_in_terminal(self, source_type, path):
        source_type_key = str(source_type or "").strip().casefold()
        if source_type_key in self.TERMINAL_TOOL_TYPES:
            return True
        ext = os.path.splitext(str(path or "").strip())[1].lower()
        return ext in {".bat", ".cmd", ".ps1", ".py"}

    def _infer_type_label(self, path, source_type, is_web_tool):
        return infer_import_tool_type_label(
            path,
            source_type=source_type,
            is_web_tool=is_web_tool,
            terminal_source_types=self.TERMINAL_TOOL_TYPES,
            document_extensions=self.DOCUMENT_EXTENSIONS,
        )

    def _map_tianhu_category(self, raw_tool):
        source_category = str(raw_tool.get("category", "") or "").strip()
        source_type = str(raw_tool.get("type", "") or "").strip()
        raw_url = str(raw_tool.get("url", "") or "").strip()
        raw_path = str(raw_tool.get("path", "") or "").strip()
        is_web_tool = self._is_tianhu_web_tool(source_type, raw_url, raw_path)
        keyword_text = self._build_tianhu_keyword_text(raw_tool)

        for keywords, mapped_result in self.TIANHU_CATEGORY_MATCH_RULES:
            if self._contains_any(keyword_text, keywords):
                return mapped_result

        mapped = self.TIANHU_CATEGORY_FALLBACK_RULES.get(source_category.casefold())
        if mapped:
            return mapped

        if is_web_tool:
            return "靶场与资源导航", "导航站点"

        return self.TIANHU_DEFAULT_FALLBACK_CATEGORY, ""

    def _build_tianhu_keyword_text(self, raw_tool):
        fields = [
            raw_tool.get("name", ""),
            raw_tool.get("category", ""),
            raw_tool.get("type", ""),
            raw_tool.get("description", ""),
            raw_tool.get("group", ""),
            raw_tool.get("path", ""),
            raw_tool.get("url", ""),
        ]
        tags = raw_tool.get("tags")
        if isinstance(tags, list):
            fields.extend(tags)
        elif tags:
            fields.append(str(tags))
        return " ".join(str(field or "").strip() for field in fields).casefold()

    def _contains_any(self, text, keywords):
        return any(str(keyword).casefold() in text for keyword in keywords)

    def _resolve_category_assignment(self, categories, category_name, subcategory_name):
        category = self._match_named_item(categories, category_name)
        if not category:
            return None, None, "", ""

        category_id = category.get("id")
        resolved_category_name = category.get("name", "")

        if not subcategory_name:
            return category_id, None, resolved_category_name, ""

        subcategory = self._match_named_item(category.get("subcategories", []) or [], subcategory_name)
        if not subcategory:
            return category_id, None, resolved_category_name, ""

        return (
            category_id,
            subcategory.get("id"),
            resolved_category_name,
            subcategory.get("name", ""),
        )

    def _ensure_tianhu_tool_subcategory(self, categories, tool):
        category_id = tool.get("category_id")
        subcategory_id = tool.get("subcategory_id")
        if category_id is not None and subcategory_id is not None:
            return False

        category = None
        if category_id is not None:
            category = next(
                (item for item in categories if item.get("id") == category_id),
                None,
            )

        if category is None:
            mapped_category_name = tool.get("_mapped_category_name", "")
            category = self._match_named_item(categories, mapped_category_name)

        if category is None:
            category = self._match_named_item(categories, self.TIANHU_DEFAULT_FALLBACK_CATEGORY)

        if category is None:
            return False

        tool["category_id"] = category.get("id")
        tool["_resolved_category_name"] = category.get("name", "")

        if subcategory_id is not None:
            return False

        placeholder_subcategory, created = self._ensure_tianhu_placeholder_subcategory(categories, category)
        if placeholder_subcategory is None:
            return False

        tool["subcategory_id"] = placeholder_subcategory.get("id")
        tool["_resolved_subcategory_name"] = placeholder_subcategory.get("name", "")
        return created

    def _ensure_tianhu_placeholder_subcategory(self, categories, category):
        subcategories = category.get("subcategories")
        if not isinstance(subcategories, list):
            subcategories = []
            category["subcategories"] = subcategories

        existing = self._match_named_item(subcategories, self.TIANHU_UNCLASSIFIED_SUBCATEGORY)
        if existing:
            return existing, False

        existing_ids = {
            sub.get("id")
            for item in categories
            for sub in item.get("subcategories", []) or []
            if sub.get("id") is not None
        }
        next_id = max(existing_ids) + 1 if existing_ids else self._to_int(category.get("id"), 0) * 100 + 1
        next_priority = max(
            (self._to_int(sub.get("priority"), 0) for sub in subcategories if isinstance(sub, dict)),
            default=0,
        ) + 1

        placeholder = {
            "id": next_id,
            "name": self.TIANHU_UNCLASSIFIED_SUBCATEGORY,
            "priority": next_priority,
            "parent_id": category.get("id"),
        }
        subcategories.append(placeholder)
        return placeholder, True

    def _sanitize_category_assignment(self, categories, category_id, subcategory_id):
        for category in categories or []:
            if category.get("id") != category_id:
                continue
            valid_subcategory_ids = {
                subcategory.get("id")
                for subcategory in category.get("subcategories", []) or []
                if subcategory.get("id") is not None
            }
            if subcategory_id in valid_subcategory_ids:
                return category_id, subcategory_id
            return category_id, None
        return None, None

    def _match_named_item(self, items, target_name):
        target_text = str(target_name or "").strip()
        if not target_text:
            return None

        normalized_target = self._normalize_name(target_text)
        for item in items:
            if self._normalize_name(item.get("name", "")) == normalized_target:
                return item

        for item in items:
            normalized_item = self._normalize_name(item.get("name", ""))
            if normalized_target in normalized_item or normalized_item in normalized_target:
                return item

        return None

    def _normalize_name(self, value):
        text = str(value or "").strip().casefold()
        text = re.sub(r"[\s\-_/\\()（）【】\[\]&·.,]+", "", text)
        return text

    def _normalize_tags(self, tags):
        if isinstance(tags, str):
            tags = [tags]
        return self._deduplicate_strings(
            [str(tag).strip() for tag in (tags or []) if str(tag).strip()]
        )

    def _deduplicate_strings(self, values):
        result = []
        seen = set()
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    def _tool_fingerprint(self, tool):
        name = str(tool.get("name", "") or "").strip().casefold()
        is_web = self._to_bool(tool.get("is_web_tool", False))
        path = str(tool.get("path", "") or "").strip().casefold()
        return name, is_web, path

    def _sync_key(self, value):
        text = str(value or "").strip()
        return text.casefold() if text else ""

    def _merge_official_tool(self, existing_tool, incoming_tool, sync_id):
        merged = dict(existing_tool or {})
        merged.update(incoming_tool or {})

        merged["id"] = existing_tool.get("id")
        merged["usage_count"] = existing_tool.get("usage_count", 0)
        merged["last_used"] = existing_tool.get("last_used")
        merged["is_favorite"] = self._to_bool(existing_tool.get("is_favorite", False))

        existing_background = str(existing_tool.get("background_image", "") or "").strip()
        incoming_background = str(incoming_tool.get("background_image", "") or "").strip()
        if existing_background and not incoming_background:
            merged["background_image"] = existing_background

        if sync_id:
            merged["sync_id"] = str(sync_id).strip()
        elif existing_tool.get("sync_id"):
            merged["sync_id"] = str(existing_tool.get("sync_id")).strip()

        merged["sync_source"] = "official"
        return merged

    def _backup_tools_snapshot(self, tools, source_url):
        config_root = os.path.abspath(os.path.join(self.data_manager.data_dir, os.pardir))
        backup_root = os.path.join(config_root, "backups", "official_sync")
        os.makedirs(backup_root, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_root, f"tools_before_sync_{timestamp}.json")
        payload = {
            "schema": self.EXPORT_SCHEMA,
            "version": self.EXPORT_VERSION,
            "source": "zifeiyu-local-backup",
            "backup_type": "before_official_sync",
            "backup_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source_url": str(source_url or "").strip(),
            "tool_count": len(tools or []),
            "tools": list(tools or []),
        }
        self._write_json(backup_path, payload)
        return backup_path

    def _fetch_remote_json(self, source_url, cancel_requested=None, progress_callback=None):
        raise_if_cancelled(cancel_requested, "已取消同步官方工具库。")
        request = Request(
            source_url,
            headers={
                "User-Agent": "zifeiyu-toolkit-sync/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=self.REMOTE_JSON_TIMEOUT_SECONDS) as response:
                self._report_progress(progress_callback, "正在读取官方工具库响应...")
                raw = b"".join(
                    iter_response_chunks(
                        response,
                        cancel_requested=cancel_requested,
                        chunk_size=self.REMOTE_JSON_CHUNK_SIZE,
                    )
                )
        except HTTPError as exc:
            raise ValueError(f"官方工具库请求失败（HTTP {exc.code}）：{source_url}") from exc
        except URLError as exc:
            raise ValueError(f"官方工具库请求失败：{exc.reason}") from exc
        except OSError as exc:
            raise ValueError(f"官方工具库请求失败：{exc}") from exc

        try:
            self._report_progress(progress_callback, "正在解析官方工具库...")
            return json.loads(raw.decode("utf-8-sig"))
        except (UnicodeDecodeError, ValueError, TypeError) as exc:
            raise ValueError("官方工具库返回内容不是有效 JSON。") from exc

    def _is_tianhu_tool(self, tool):
        import_source = str(tool.get("import_source", "") or "").strip().casefold()
        if import_source == "tianhu":
            return True

        for tag in self._normalize_tags(tool.get("tags")):
            if str(tag).strip().casefold() == self.TIANHU_IMPORT_TAG.casefold():
                return True
        return False

    def _build_category_maps(self, categories):
        category_map = {}
        subcategory_map = {}
        for category in categories:
            category_id = category.get("id")
            if category_id is not None:
                category_map[category_id] = category
            for subcategory in category.get("subcategories", []) or []:
                subcategory_id = subcategory.get("id")
                if subcategory_id is not None:
                    subcategory_map[subcategory_id] = subcategory
        return category_map, subcategory_map

    def _next_tool_id(self, tools):
        return max((tool.get("id") or 0) for tool in tools) + 1 if tools else 1

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    def _to_int(self, value, default=0):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return default

    def _read_json(self, file_path):
        with open(file_path, "r", encoding="utf-8-sig") as file:
            return json.load(file)

    def _write_json(self, file_path, payload):
        target_path = os.path.abspath(file_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
