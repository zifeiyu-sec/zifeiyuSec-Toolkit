import json
import os
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from core.task_control import iter_response_chunks, raise_if_cancelled


class ToolConfigExchangeService:
    EXPORT_SCHEMA = "zifeiyu-toolkit-tools"
    EXPORT_VERSION = 2
    DEFAULT_ICON = "write-github.svg"
    TIANHU_IMPORT_TAG = "天狐导入"
    TIANHU_DEFAULT_ICON = "fox.ico"
    TIANHU_SUPPORTED_VERSION = "2.0"
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
    TERMINAL_TOOL_TYPES = {"命令行", "python", "批处理"}
    JAVA8_GUI_TYPE = "java8(图形化)"
    JAVA11_GUI_TYPE = "java11(图形化)"
    DOCUMENT_EXTENSIONS = {
        ".txt", ".md", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".ppt", ".pptx", ".csv", ".json", ".yaml", ".yml",
    }
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
        "网页工具": ("靶场与资源导航", "导航站点"),
        "其他工具": ("开发与效率工具", "通用开发工具"),
    }
    TIANHU_CATEGORY_MATCH_RULES = [
        (("webshell", "冰蝎", "哥斯拉", "蚁剑", "中国蚁剑", "behinder", "godzilla", "antsword", "alien", "cknife", "webshell管理"), ("Web 安全测试", "WebShell 管理")),
        (("burp", "mitmproxy", "fiddler", "proxifier", "charles", "wireshark", "http toolkit", "reqable", "yakit"), ("Web 安全测试", "抓包与安全代理")),
        (("frp", "gost", "nps", "clash", "v2ray", "xray", "chisel", "ligolo", "suo5"), ("内网与域安全", "代理与隧道")),
        (("sqlmap", "sql注入", "super sql", "ghauri", "bbqsql"), ("Web 安全测试", "SQL 注入")),
        (("shiro", "fastjson", "jackson", "deserial", "ysoserial", "反序列化"), ("Web 安全测试", "反序列化工具")),
        (("fofa", "hunter", "quake", "zoomeye", "shodan", "censys", "criminalip", "fullhunt", "netlas", "daydaymap", "binaryedge", "threatbook"), ("情报侦察与 OSINT", "网络空间测绘")),
        (("oneforall", "subfinder", "amass", "ksubdomain", "subdomain"), ("情报侦察与 OSINT", "子域名与资产发现")),
        (("dirsearch", "gobuster", "feroxbuster", "dirbuster", "sensitive", "敏感文件"), ("情报侦察与 OSINT", "目录与敏感文件扫描")),
        (("whatweb", "ehole", "wappalyzer", "finger", "指纹", "webanalyzer"), ("情报侦察与 OSINT", "指纹识别")),
        (("whois", "备案", "icp"), ("情报侦察与 OSINT", "ICP备案与注册信息")),
        (("零零信安", "0.zone", "haveibeenpwned", "泄露", "暗网"), ("情报侦察与 OSINT", "社工与泄露情报")),
        (("blueteamtools", "蓝队分析辅助工具箱"), ("蓝队分析与应急响应", "蓝队综合工具")),
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
            self.data_manager.save_tools(existing_tools)

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

    def import_tianhu_tools(self, source_path):
        tools_payload, settings, source_root, detected_version = self._load_tianhu_payload(source_path)
        categories = list(self.data_manager.load_categories() or [])

        existing_tools = list(self.data_manager.load_tools() or [])
        next_id = self._next_tool_id(existing_tools)
        seen_fingerprints = {self._tool_fingerprint(tool) for tool in existing_tools}

        imported_tools = []
        skipped = 0
        category_stats = {}
        categories_changed = False

        for raw_tool in tools_payload:
            normalized = self._convert_tianhu_tool(raw_tool, source_root, settings, categories)
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
            self.data_manager.save_tools(existing_tools)

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
            if detected_version != self.TIANHU_SUPPORTED_VERSION:
                raise ValueError("当前仅支持导入天狐 2.0 导出配置，请确认导出文件来自天狐 2.0。")
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
            if detected_version != self.TIANHU_SUPPORTED_VERSION:
                raise ValueError("当前仅支持导入天狐 2.0 导出配置，请确认目录来自天狐 2.0。")
            return tools_payload, settings, normalized_source, detected_version

        raise FileNotFoundError(f"天狐配置不存在: {source_text}")

    def _detect_tianhu_version(self, payload, tools_payload):
        if not isinstance(payload, dict) or not tools_payload or not isinstance(tools_payload, list):
            return ""

        valid_tools = [
            item for item in tools_payload
            if isinstance(item, dict) and self.TIANHU2_REQUIRED_TOOL_FIELDS.issubset(item.keys())
        ]
        if not valid_tools or len(valid_tools) != len(tools_payload):
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

    def _convert_tianhu_tool(self, raw_tool, tianhu_root, settings, categories):
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
            "icon": self.TIANHU_DEFAULT_ICON,
            "is_favorite": False,
            "arguments": params,
            "working_directory": working_directory,
            "run_in_terminal": self._should_run_in_terminal(source_type, final_path),
            "is_web_tool": is_web_tool,
            "type_label": self._infer_type_label(final_path, source_type, is_web_tool),
            "usage_count": 0,
            "last_used": None,
            "import_source": "tianhu",
            "import_source_version": self.TIANHU_SUPPORTED_VERSION,
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
            return os.path.normpath(normalized)

        if tianhu_root:
            normalized = normalized.lstrip("\\/")
            return os.path.normpath(os.path.join(tianhu_root, normalized))
        return os.path.normpath(normalized)

    def _derive_working_directory(self, path):
        absolute_path = os.path.abspath(path)
        if os.path.isdir(absolute_path) or self._path_looks_like_directory(path):
            return absolute_path
        return os.path.dirname(absolute_path) or absolute_path

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
        if is_web_tool:
            return "网页"

        source_type_key = str(source_type or "").strip().casefold()
        if source_type_key in self.TERMINAL_TOOL_TYPES:
            return "终端"

        if path and (os.path.isdir(path) or self._path_looks_like_directory(path)):
            return "目录"

        ext = os.path.splitext(str(path or "").strip())[1].lower()
        if ext in self.DOCUMENT_EXTENSIONS:
            return "文档"

        return "应用"

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
