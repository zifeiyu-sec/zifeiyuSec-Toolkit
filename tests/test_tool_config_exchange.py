import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from core.data_manager import DataManager
from core.tool_config_exchange import ToolConfigExchangeService


class _FakeResponse:
    def __init__(self, data, content_type, final_url):
        self._data = data
        self._final_url = final_url
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._data

    def geturl(self):
        return self._final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ToolConfigExchangeTests(unittest.TestCase):
    def setUp(self):
        self.config_dir = make_test_dir(f"tool_exchange_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.config_dir))
        self.data_manager = DataManager(config_dir=str(self.config_dir))
        self.exchange = ToolConfigExchangeService(self.data_manager)

        categories = [
            {
                "id": 1,
                "name": "情报侦察与 OSINT",
                "priority": 1,
                "subcategories": [
                    {"id": 101, "name": "网络空间测绘", "priority": 1},
                    {"id": 107, "name": "企业与实名信息", "priority": 2},
                    {"id": 108, "name": "ICP备案与注册信息", "priority": 3},
                    {"id": 110, "name": "在线网络探测", "priority": 4},
                ],
            },
            {
                "id": 2,
                "name": "漏洞扫描与利用",
                "priority": 2,
                "subcategories": [
                    {"id": 201, "name": "综合漏洞扫描", "priority": 1},
                    {"id": 202, "name": "漏洞验证与 PoC", "priority": 2},
                    {"id": 203, "name": "端口与服务扫描", "priority": 3},
                ],
            },
            {
                "id": 3,
                "name": "Web 安全测试",
                "priority": 3,
                "subcategories": [
                    {"id": 301, "name": "抓包与安全代理", "priority": 1},
                    {"id": 302, "name": "WebShell 管理", "priority": 2},
                    {"id": 303, "name": "注入类漏洞", "priority": 3},
                    {"id": 305, "name": "API 接口测试", "priority": 4},
                    {"id": 306, "name": "反序列化与RCE", "priority": 5},
                ],
            },
            {
                "id": 4,
                "name": "内网与域安全",
                "priority": 4,
                "subcategories": [
                    {"id": 401, "name": "代理与隧道", "priority": 1},
                    {"id": 405, "name": "C2 与远控", "priority": 2},
                    {"id": 406, "name": "免杀与对抗", "priority": 3},
                ],
            },
            {
                "id": 5,
                "name": "密码学与凭据",
                "priority": 5,
                "subcategories": [
                    {"id": 504, "name": "编码解码与数据处理", "priority": 1},
                    {"id": 505, "name": "加密解密工具", "priority": 2},
                ],
            },
            {
                "id": 6,
                "name": "蓝队分析与应急响应",
                "priority": 5,
                "subcategories": [
                    {"id": 601, "name": "检测与分析", "priority": 1},
                    {"id": 602, "name": "终端安全", "priority": 2},
                    {"id": 603, "name": "应急响应", "priority": 3},
                    {"id": 604, "name": "恶意代码分析", "priority": 4},
                    {"id": 605, "name": "数字取证", "priority": 5},
                    {"id": 606, "name": "安全运营", "priority": 6},
                    {"id": 607, "name": "威胁情报与关联分析", "priority": 7},
                    {"id": 608, "name": "蓝队综合工具", "priority": 8},
                ],
            },
            {
                "id": 7,
                "name": "开发与效率工具",
                "priority": 6,
                "subcategories": [
                    {"id": 702, "name": "网络调试", "priority": 1},
                    {"id": 708, "name": "通用开发工具", "priority": 2},
                ],
            },
            {
                "id": 9,
                "name": "靶场与资源导航",
                "priority": 7,
                "subcategories": [
                    {"id": 902, "name": "安全社区与论坛", "priority": 1},
                    {"id": 904, "name": "漏洞库与情报库", "priority": 2},
                    {"id": 905, "name": "导航站点", "priority": 3},
                ],
            },
            {
                "id": 15,
                "name": "AI 安全与大模型",
                "priority": 8,
                "subcategories": [
                    {"id": 1505, "name": "Agent 与自动化", "priority": 1},
                ],
            },
        ]
        self.assertTrue(self.data_manager.save_categories(categories))
        self.assertTrue(self.data_manager.save_tools([]))

    def _write_json(self, file_name, payload):
        target = self.config_dir / file_name
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    def _build_tianhu_v2_payload(self, tools, categories=None, settings=None):
        return {
            "categories": categories or [
                "最近启动",
                "我的收藏",
                "信息收集工具",
                "其他工具",
                "网页工具",
            ],
            "settings": settings or {
                "python_path": r"C:\Security\TH2\python\python.exe",
                "java8_path": r"C:\Security\TH2\jre8\bin\java.exe",
                "java11_path": r"C:\Security\TH2\jre11\bin\java.exe",
                "custom_interpreters": [],
                "favorite_tools": [],
                "recent_tools": [],
                "theme": "dark",
                "display_mode": "grid",
                "update_check": False,
            },
            "tools": tools,
        }

    def _build_tianhu_v3_payload(self, tools):
        return list(tools)

    def test_export_native_tools_is_config_only_and_sorted(self):
        tools = [
            {
                "id": 2,
                "name": "Zeta",
                "path": "tools/zeta.exe",
                "description": "local tool",
                "category_id": 2,
                "subcategory_id": 201,
                "tags": ["scan", "zeta"],
                "is_favorite": False,
                "arguments": "--help",
                "working_directory": "tools",
                "run_in_terminal": True,
                "is_web_tool": False,
                "type_label": "终端",
                "usage_count": 99,
                "last_used": "2026-01-01T00:00:00Z",
                "import_source": "tianhu",
                "source_category": "漏洞扫描与利用工具",
                "custom_interpreter_path": "python.exe",
                "custom_interpreter_type": "python",
            },
            {
                "id": 1,
                "name": "Alpha",
                "path": "https://example.com",
                "description": "web tool",
                "category_id": 1,
                "subcategory_id": 101,
                "tags": ["osint"],
                "is_favorite": True,
                "arguments": "",
                "working_directory": "",
                "run_in_terminal": False,
                "is_web_tool": True,
                "type_label": "网页",
                "usage_count": 10,
                "last_used": "2026-01-02T00:00:00Z",
            },
        ]
        self.assertTrue(self.data_manager.save_tools(tools))

        export_path = self.config_dir / "export.json"
        result = self.exchange.export_native_tools(str(export_path))
        payload = json.loads(export_path.read_text(encoding="utf-8"))

        self.assertEqual("config_only", result["mode"])
        self.assertEqual(2, payload["version"])
        self.assertEqual("config_only", payload["export_mode"])
        self.assertEqual(["Alpha", "Zeta"], [tool["name"] for tool in payload["tools"]])
        self.assertNotIn("usage_count", payload["tools"][0])
        self.assertNotIn("last_used", payload["tools"][0])
        self.assertNotIn("import_source", payload["tools"][1])
        self.assertEqual("情报侦察与 OSINT", payload["tools"][0]["category_name"])
        self.assertEqual("python", payload["tools"][1]["custom_interpreter_type"])

    def test_import_native_tools_maps_category_by_name_and_resets_runtime_fields(self):
        payload = {
            "schema": "zifeiyu-toolkit-tools",
            "version": 2,
            "source": "zifeiyu",
            "export_mode": "config_only",
            "tools": [
                {
                    "name": "Imported Tool",
                    "path": "tools/imported.exe",
                    "description": "imported",
                    "category_id": 999,
                    "subcategory_id": 9999,
                    "category_name": "情报侦察与 OSINT",
                    "subcategory_name": "网络空间测绘",
                    "tags": ["imported"],
                    "is_favorite": True,
                    "arguments": "--run",
                    "working_directory": "tools",
                    "run_in_terminal": False,
                    "is_web_tool": False,
                    "type_label": "应用",
                    "usage_count": 777,
                    "last_used": "2026-01-01T00:00:00Z",
                    "import_source": "legacy",
                }
            ],
        }
        import_path = self._write_json("import.json", payload)

        result = self.exchange.import_native_tools(str(import_path))
        self.assertEqual(1, result["imported"])

        imported_tool = self.data_manager.load_tools()[0]
        self.assertEqual(1, imported_tool["category_id"])
        self.assertEqual(101, imported_tool["subcategory_id"])
        self.assertEqual(0, imported_tool["usage_count"])
        self.assertIsNone(imported_tool["last_used"])
        self.assertNotIn("import_source", imported_tool)

    def test_import_native_tools_rejects_tianhu_payload(self):
        payload = {
            "source": "tianhu",
            "tools": [],
        }
        import_path = self._write_json("tianhu.json", payload)

        with self.assertRaises(ValueError):
            self.exchange.import_native_tools(str(import_path))

    def test_import_native_tools_raises_when_save_fails(self):
        payload = {
            "schema": "zifeiyu-toolkit-tools",
            "version": 2,
            "source": "zifeiyu",
            "export_mode": "config_only",
            "tools": [
                {
                    "name": "Save Failure",
                    "path": "tools/save-failure.exe",
                    "description": "imported",
                    "category_name": "情报侦察与 OSINT",
                    "subcategory_name": "网络空间测绘",
                    "type_label": "应用",
                }
            ],
        }
        import_path = self._write_json("import-save-failure.json", payload)

        with patch.object(self.data_manager, "save_tools", return_value=False):
            with self.assertRaisesRegex(OSError, "导入原生工具配置失败"):
                self.exchange.import_native_tools(str(import_path))

    def test_import_tianhu_v2_maps_known_tools_and_creates_placeholder_for_unknown_tools(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "FOFA",
                "category": "信息收集工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "空间测绘入口",
                "group": "内置工具",
                "params": "",
                "path": "",
                "tags": ["fofa"],
                "type": "网页",
                "url": "https://fofa.info",
                "weight": 1,
            },
            {
                "name": "CustomLocalTool",
                "category": "自定义工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "用户自定义工具",
                "group": "自定义分组",
                "params": "--help",
                "path": r"tools\custom.exe",
                "tags": ["custom"],
                "type": "应用",
                "url": "",
                "weight": 2,
            },
        ])
        import_path = self._write_json("tianhu_v2.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(2, result["imported"])
        self.assertEqual("2.0", result["detected_version"])
        self.assertTrue(result["created_placeholder_subcategory"])

        tools_by_name = {tool["name"]: tool for tool in self.data_manager.load_tools()}
        fofa = tools_by_name["FOFA"]
        custom_tool = tools_by_name["CustomLocalTool"]

        self.assertEqual(1, fofa["category_id"])
        self.assertEqual(101, fofa["subcategory_id"])
        self.assertTrue(fofa["is_web_tool"])
        self.assertEqual("https://fofa.info", fofa["path"])
        self.assertEqual("tianhu", fofa["import_source"])
        self.assertEqual("2.0", fofa["import_source_version"])

        self.assertEqual(7, custom_tool["category_id"])
        self.assertEqual("tianhu", custom_tool["import_source"])
        self.assertEqual("2.0", custom_tool["import_source_version"])
        self.assertEqual(
            os.path.normcase(r"C:\Security\TH2\tools\custom.exe"),
            os.path.normcase(custom_tool["path"]),
        )

        categories = self.data_manager.load_categories()
        dev_category = next(category for category in categories if category["id"] == 7)
        placeholder = next(
            subcategory
            for subcategory in dev_category["subcategories"]
            if subcategory["name"] == self.exchange.TIANHU_UNCLASSIFIED_SUBCATEGORY
        )
        self.assertEqual(placeholder["id"], custom_tool["subcategory_id"])

    def test_import_tianhu_v2_uses_registry_icon_when_tool_name_matches(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "BurpSuit-Pro",
                "category": "抓包与代理工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "Burp proxy",
                "group": "Web",
                "params": "",
                "path": "",
                "tags": ["burp"],
                "type": "网页",
                "url": "https://portswigger.net/burp",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_v2_burp.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        self.assertEqual("2.0", result["detected_version"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual("tianhu/common/burp.png", imported["icon"])

    def test_import_tianhu_uses_local_icon_library_by_normalized_tool_name(self):
        payload = self._build_tianhu_v3_payload([
            {
                "name": "DirSearch目录探测工具",
                "category": "信息收集工具",
                "description": "directory scanner",
                "group": "Web",
                "params": "",
                "path": "",
                "tags": ["dirsearch"],
                "type": "GUI应用",
                "url": "",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_v3_dirsearch_icon.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual("tianhu/3.0/dirsearch.svg", imported["icon"])

    def test_import_tianhu_prefers_tool_name_icon_library_key_before_legacy_aliases(self):
        payload = self._build_tianhu_v3_payload([
            {
                "name": "Zoomeye(钟馗之眼)",
                "category": "网页工具",
                "description": "space search",
                "group": "Web",
                "params": "",
                "path": "",
                "tags": ["zoomeye"],
                "type": "网页",
                "url": "https://www.zoomeye.org",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_v3_zoomeye_icon.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual("tianhu/common/zoomeye.ico", imported["icon"])

    def test_import_tianhu_v2_searches_web_for_missing_icons_before_defaulting(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "LegacyUnknownTool",
                "category": "其他工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "unknown legacy",
                "group": "misc",
                "params": "",
                "path": "",
                "tags": ["unknown"],
                "type": "GUI应用",
                "url": "",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_v2_search.json", payload)

        with patch.object(self.exchange, "_search_tianhu_icon_source_url", return_value="https://legacy.example/tool"):
            with patch.object(self.exchange, "_download_tianhu_web_icon", return_value="legacy.ico"):
                result = self.exchange.import_tianhu_tools(str(import_path), download_missing_icons=True)

        self.assertEqual(1, result["imported"])
        self.assertEqual("2.0", result["detected_version"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual("legacy.ico", imported["icon"])

    def test_import_tianhu_v3_top_level_list_uses_icons_and_maps_emergency_category(self):
        payload = self._build_tianhu_v3_payload([
            {
                "name": "FOFA",
                "category": "网页工具",
                "description": "空间测绘入口",
                "group": "内置工具",
                "params": "",
                "path": "",
                "tags": ["fofa"],
                "type": "网页",
                "url": "https://fofa.info",
                "weight": 1,
            },
            {
                "name": "WinLogCheckV3.4.1",
                "category": "应急响应",
                "description": "日志分析",
                "group": "应急响应",
                "params": "",
                "path": r"/tools/gui_yjxy/WinLogCheckV3.4.1.exe",
                "tags": ["log"],
                "type": "GUI应用",
                "url": "",
                "weight": 2,
            },
            {
                "name": "Nmap",
                "category": "漏洞扫描与利用工具",
                "description": "端口扫描",
                "group": "内置工具",
                "params": "-h",
                "path": r"/tools/gui_other/nmap/nmap.exe",
                "tags": ["nmap"],
                "type": "命令行",
                "url": "",
                "weight": 3,
            },
        ])
        import_path = self._write_json("tianhu_v3.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(3, result["imported"])
        self.assertEqual("3.0", result["detected_version"])

        tools_by_name = {tool["name"]: tool for tool in self.data_manager.load_tools()}
        fofa = tools_by_name["FOFA"]
        winlog = tools_by_name["WinLogCheckV3.4.1"]
        nmap = tools_by_name["Nmap"]

        self.assertEqual(1, fofa["category_id"])
        self.assertEqual(101, fofa["subcategory_id"])
        self.assertEqual("tianhu/common/fofa.ico", fofa["icon"])
        self.assertTrue(fofa["is_web_tool"])

        self.assertEqual(6, winlog["category_id"])
        self.assertEqual(603, winlog["subcategory_id"])
        self.assertEqual("tianhu/3.0/winlogcheckv3_4_1.svg", winlog["icon"])

        self.assertEqual(2, nmap["category_id"])
        self.assertEqual(203, nmap["subcategory_id"])
        self.assertEqual("tianhu/common/nmap.png", nmap["icon"])
        self.assertEqual(os.path.normpath(r"tools\gui_other\nmap\nmap.exe"), os.path.normpath(nmap["path"]))

    def test_import_tianhu_v3_uses_downloaded_icon_when_no_local_match_exists(self):
        payload = self._build_tianhu_v3_payload([
            {
                "name": "NoLocalIconTool",
                "category": "应急响应",
                "description": "应急分析入口",
                "group": "应急工具",
                "params": "",
                "path": "",
                "tags": ["missing-icon"],
                "type": "网页",
                "url": "https://missing-icon-test.invalid/tool/",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_v3_download.json", payload)

        with patch.object(self.exchange, "_download_tianhu_web_icon", return_value="findall.ico"):
            result = self.exchange.import_tianhu_tools(str(import_path), download_missing_icons=True)

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual("findall.ico", imported["icon"])
        self.assertEqual(6, imported["category_id"])
        self.assertEqual(603, imported["subcategory_id"])

    def test_import_tianhu_v3_uses_registry_icon_when_tool_name_matches(self):
        payload = self._build_tianhu_v3_payload([
            {
                "name": "BurpSuit-Pro",
                "category": "Web 安全测试",
                "description": "Burp",
                "group": "Web",
                "params": "",
                "path": "",
                "tags": ["burp"],
                "type": "网页",
                "url": "",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_v3_burp.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual("tianhu/common/burp.png", imported["icon"])

    def test_import_tianhu_v3_searches_web_for_missing_icons_before_defaulting(self):
        payload = self._build_tianhu_v3_payload([
            {
                "name": "UnknownToolX",
                "category": "漏洞扫描与利用工具",
                "description": "unknown",
                "group": "misc",
                "params": "",
                "path": "",
                "tags": ["unknown"],
                "type": "GUI应用",
                "url": "",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_v3_search.json", payload)

        with patch.object(self.exchange, "_search_tianhu_icon_source_url", return_value="https://unknown.example/tool"):
            with patch.object(self.exchange, "_download_tianhu_web_icon", return_value="unknown.ico"):
                result = self.exchange.import_tianhu_tools(str(import_path), download_missing_icons=True)

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual("unknown.ico", imported["icon"])

    def test_download_tianhu_web_icon_rejects_html_payload(self):
        icon_dir = self.config_dir / "downloaded_icons"
        fake_html = b"<!doctype html><html><body>blocked</body></html>"

        with patch(
            "core.tool_config_exchange.urlopen",
            return_value=_FakeResponse(
                fake_html,
                "image/x-icon",
                "https://example.com/favicon.ico",
            ),
        ):
            result = self.exchange._download_tianhu_web_icon(
                "https://example.com/tool",
                icon_dir=icon_dir,
                target_name="example",
            )

        self.assertEqual("", result)
        self.assertEqual([], list(icon_dir.glob("*")) if icon_dir.exists() else [])

    def test_import_tianhu_bare_command_keeps_empty_working_directory(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "nmap",
                "category": "漏洞扫描与利用工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "PATH command",
                "group": "CLI",
                "params": "-h",
                "path": "nmap",
                "tags": ["nmap"],
                "type": "应用",
                "url": "",
                "weight": 1,
            }
        ], settings={
            "python_path": "",
            "java8_path": "",
            "java11_path": "",
            "custom_interpreters": [],
            "favorite_tools": [],
            "recent_tools": [],
            "theme": "dark",
            "display_mode": "grid",
            "update_check": False,
        })
        import_path = self._write_json("tianhu_nmap_command.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual("nmap", imported["path"])
        self.assertEqual("", imported["working_directory"])

    def test_import_tianhu_tools_raises_when_save_fails(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "FOFA",
                "category": "信息收集工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "空间测绘入口",
                "group": "内置工具",
                "params": "",
                "path": "",
                "tags": ["fofa"],
                "type": "网页",
                "url": "https://fofa.info",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu-save-failure.json", payload)

        with patch.object(self.data_manager, "save_tools", return_value=False):
            with self.assertRaisesRegex(OSError, "导入天狐工具失败"):
                self.exchange.import_tianhu_tools(str(import_path))

    def test_import_tianhu_v2_maps_sqlmap_to_injection_subcategory(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "SQLMAP X Plus",
                "category": "漏洞扫描与利用工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "SQL 注入测试",
                "group": "内置工具",
                "params": "",
                "path": r"tools\sqlmap\sqlmap.py",
                "tags": ["sqlmap"],
                "type": "Python",
                "url": "",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_sqlmap_v2.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual(3, imported["category_id"])
        self.assertEqual(303, imported["subcategory_id"])

    def test_import_tianhu_v2_maps_fastjson_to_deserialization_tools(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "Fastjson Helper",
                "category": "漏洞扫描与利用工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "Fastjson 反序列化利用",
                "group": "内置工具",
                "params": "",
                "path": r"tools\fastjson\helper.jar",
                "tags": ["fastjson"],
                "type": "Java",
                "url": "",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_fastjson_v2.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual(3, imported["category_id"])
        self.assertEqual(306, imported["subcategory_id"])

    def test_import_tianhu_v2_avoids_oa_false_positive_for_maloader(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "MaLoader免杀工具",
                "category": "免杀工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "免杀生成",
                "group": "内置工具",
                "params": "",
                "path": r"tools\maloader\app.exe",
                "tags": ["maloader"],
                "type": "GUI应用",
                "url": "",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_maloader_v2.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual(4, imported["category_id"])
        self.assertEqual(406, imported["subcategory_id"])

    def test_import_tianhu_v2_maps_httpx_by_rule_table_to_osint_collection(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "httpx",
                "category": "其他工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "HTTP 探测工具",
                "group": "内置工具",
                "params": "",
                "path": r"tools\httpx\httpx.exe",
                "tags": ["probe"],
                "type": "应用",
                "url": "",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_httpx_v2.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        self.assertTrue(result["created_placeholder_subcategory"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual(1, imported["category_id"])
        self.assertIsNotNone(imported["subcategory_id"])

    def test_import_tianhu_v2_maps_web_tool_to_navigation_when_no_keyword_rule_matches(self):
        payload = self._build_tianhu_v2_payload([
            {
                "name": "Unknown Security Portal",
                "category": "自定义工具",
                "custom_interpreter_name": "",
                "custom_interpreter_type": "",
                "description": "一个未命中规则的网页工具",
                "group": "自定义分组",
                "params": "",
                "path": "",
                "tags": ["portal"],
                "type": "网页",
                "url": "https://portal.example.com",
                "weight": 1,
            }
        ])
        import_path = self._write_json("tianhu_unknown_web_v2.json", payload)

        result = self.exchange.import_tianhu_tools(str(import_path))

        self.assertEqual(1, result["imported"])
        imported = self.data_manager.load_tools()[0]
        self.assertEqual(9, imported["category_id"])
        self.assertEqual(905, imported["subcategory_id"])
        self.assertTrue(imported["is_web_tool"])

    def test_import_tianhu_v2_rejects_payload_without_tianhu_signature(self):
        payload = {
            "settings": {},
            "tools": [
                {
                    "name": "UnknownExport",
                    "category": "自定义工具",
                    "description": "not enough signature",
                    "group": "custom",
                    "params": "",
                    "path": r"tools\custom.exe",
                    "tags": [],
                    "type": "应用",
                    "url": "",
                }
            ],
        }
        import_path = self._write_json("not_tianhu_v2.json", payload)

        with self.assertRaisesRegex(ValueError, "天狐 2.0"):
            self.exchange.import_tianhu_tools(str(import_path))

    def test_remove_tianhu_tools_only_deletes_imported_entries(self):
        tools = [
            {
                "id": 1,
                "name": "Local Tool",
                "path": "tools/local.exe",
                "description": "local",
                "category_id": 1,
                "subcategory_id": 101,
                "tags": ["local"],
                "is_favorite": False,
            },
            {
                "id": 2,
                "name": "Tianhu Tool A",
                "path": "tools/tianhu-a.exe",
                "description": "from tianhu",
                "category_id": 2,
                "subcategory_id": 201,
                "tags": ["天狐导入"],
                "is_favorite": False,
                "import_source": "tianhu",
            },
            {
                "id": 3,
                "name": "Tianhu Tool B",
                "path": "tools/tianhu-b.exe",
                "description": "from old tianhu import",
                "category_id": 2,
                "subcategory_id": 202,
                "tags": ["天狐导入", "legacy"],
                "is_favorite": False,
            },
        ]
        self.assertTrue(self.data_manager.save_tools(tools))

        result = self.exchange.remove_tianhu_tools()

        self.assertEqual(2, result["removed"])
        self.assertEqual(1, result["remaining"])
        remaining_tools = self.data_manager.load_tools()
        self.assertEqual(["Local Tool"], [tool["name"] for tool in remaining_tools])

    def test_sync_official_tools_from_url_imports_new_tools_and_creates_backup(self):
        payload = {
            "schema": "zifeiyu-toolkit-tools",
            "version": 2,
            "source": "zifeiyu",
            "tools": [
                {
                    "sync_id": "official-fofa",
                    "name": "FOFA",
                    "path": "https://fofa.info",
                    "description": "OSINT",
                    "category_name": "情报侦察与 OSINT",
                    "subcategory_name": "网络空间测绘",
                    "is_web_tool": True,
                    "icon": "github_1_1_1.svg",
                    "tags": ["osint"],
                }
            ],
        }

        with patch.object(self.exchange, "_fetch_remote_json", return_value=payload):
            result = self.exchange.sync_official_tools_from_url(
                "https://example.com/tools.sync.json",
                update_existing=True,
            )

        self.assertEqual(1, result["imported"])
        self.assertEqual(0, result["updated"])
        self.assertEqual(0, result["skipped"])
        self.assertTrue(Path(result["backup_path"]).exists())

        tools = self.data_manager.load_tools()
        self.assertEqual(1, len(tools))
        self.assertEqual("official-fofa", tools[0].get("sync_id"))
        self.assertEqual("official", tools[0].get("sync_source"))

    def test_sync_official_tools_from_url_updates_existing_and_preserves_runtime_fields(self):
        existing = [
            {
                "id": 1,
                "sync_id": "official-fofa",
                "name": "FOFA",
                "path": "https://fofa.info",
                "description": "old",
                "category_id": 1,
                "subcategory_id": 101,
                "background_image": "custom.png",
                "icon": "old.svg",
                "tags": ["local-tag"],
                "is_favorite": True,
                "is_web_tool": True,
                "usage_count": 12,
                "last_used": "2026-01-01T00:00:00Z",
            }
        ]
        self.assertTrue(self.data_manager.save_tools(existing))

        payload = {
            "schema": "zifeiyu-toolkit-tools",
            "version": 2,
            "tools": [
                {
                    "sync_id": "official-fofa",
                    "name": "FOFA",
                    "path": "https://fofa.info/new",
                    "description": "new-description",
                    "category_name": "情报侦察与 OSINT",
                    "subcategory_name": "网络空间测绘",
                    "background_image": "",
                    "icon": "new.svg",
                    "tags": ["remote-tag"],
                    "is_favorite": False,
                    "is_web_tool": True,
                }
            ],
        }

        with patch.object(self.exchange, "_fetch_remote_json", return_value=payload):
            result = self.exchange.sync_official_tools_from_url(
                "https://example.com/tools.sync.json",
                update_existing=True,
            )

        self.assertEqual(0, result["imported"])
        self.assertEqual(1, result["updated"])
        self.assertEqual(0, result["skipped"])

        tool = self.data_manager.load_tools()[0]
        self.assertEqual(1, tool["id"])
        self.assertEqual(12, tool["usage_count"])
        self.assertEqual("2026-01-01T00:00:00Z", tool["last_used"])
        self.assertTrue(tool["is_favorite"])
        self.assertEqual("custom.png", tool["background_image"])
        self.assertEqual("https://fofa.info/new", tool["path"])
        self.assertNotIn("tags", tool)

    def test_sync_official_tools_from_url_can_skip_existing_updates(self):
        existing = [
            {
                "id": 1,
                "sync_id": "official-fofa",
                "name": "FOFA",
                "path": "https://fofa.info",
                "description": "old",
                "category_id": 1,
                "subcategory_id": 101,
                "icon": "old.svg",
                "tags": ["local-tag"],
                "is_favorite": True,
                "is_web_tool": True,
                "usage_count": 5,
                "last_used": "2026-01-01T00:00:00Z",
            }
        ]
        self.assertTrue(self.data_manager.save_tools(existing))

        payload = {
            "schema": "zifeiyu-toolkit-tools",
            "version": 2,
            "tools": [
                {
                    "sync_id": "official-fofa",
                    "name": "FOFA",
                    "path": "https://fofa.info/new",
                    "description": "new-description",
                    "category_name": "情报侦察与 OSINT",
                    "subcategory_name": "网络空间测绘",
                    "tags": ["remote-tag"],
                    "is_web_tool": True,
                }
            ],
        }

        with patch.object(self.exchange, "_fetch_remote_json", return_value=payload):
            result = self.exchange.sync_official_tools_from_url(
                "https://example.com/tools.sync.json",
                update_existing=False,
            )

        self.assertEqual(0, result["imported"])
        self.assertEqual(0, result["updated"])
        self.assertEqual(1, result["skipped"])
        tool = self.data_manager.load_tools()[0]
        self.assertEqual("https://fofa.info", tool["path"])
        self.assertEqual("old", tool["description"])


if __name__ == "__main__":
    unittest.main()
