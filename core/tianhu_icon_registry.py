from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus


@dataclass(frozen=True)
class TianhuIconRule:
    aliases: tuple[str, ...]
    icon: str
    source_urls: tuple[str, ...] = ()


TIANHU_ICON_RULES: tuple[TianhuIconRule, ...] = (
    TianhuIconRule(("burp suit", "burpsuit-pro", "burp"), "burpsuite_1.png", ("https://portswigger.net/burp",)),
    TianhuIconRule(("goby",), "Goby_icon.png"),
    TianhuIconRule(("nuclei",), "Nuclei_GUI_icon_1.png", ("https://github.com/projectdiscovery/nuclei",)),
    TianhuIconRule(("nmap",), "nmap.png", ("https://nmap.org",)),
    TianhuIconRule(("yakit",), "Yakit_icon.png", ("https://yakit.run",)),
    TianhuIconRule(("proxifier", "proxifire"), "Proxifier_icon_1.png", ("https://www.proxifier.com",)),
    TianhuIconRule(("wireshark",), "wireshark.ico", ("https://www.wireshark.org",)),
    TianhuIconRule(("cyberchef",), "CyberChef_icon.png", ("https://gchq.github.io/CyberChef/",)),
    TianhuIconRule(("amass",), "amass.png", ("https://github.com/owasp-amass/amass",)),
    TianhuIconRule(("fofa",), "fofa.info_favicon_1.ico", ("https://fofa.info",)),
    TianhuIconRule(("hunter", "鹰图"), "hunter.qianxin.com_favicon_1.ico", ("https://hunter.qianxin.com",)),
    TianhuIconRule(("quake", "360quake", "钟馗之眼"), "quake.ico", ("https://quake.360.net",)),
    TianhuIconRule(("shodan",), "shodan.png", ("https://www.shodan.io",)),
    TianhuIconRule(("censys",), "censys.ico", ("https://censys.io",)),
    TianhuIconRule(("ctfhub",), "ctfhub.png", ("https://www.ctfhub.com",)),
    TianhuIconRule(("ctfshow",), "ctfshow.png", ("https://ctf.show",)),
    TianhuIconRule(("foxbypass", "fox"), "fox.ico"),
    TianhuIconRule(("tianhu", "天狐"), "tianhu_import.svg"),
    TianhuIconRule(("cmd5",), "www.cmd5.com_favicon.ico", ("https://www.cmd5.com",)),
    TianhuIconRule(("github.com",), "black-github.png", ("https://github.com",)),
    TianhuIconRule(("gitee.com",), "github.com_favicon.ico", ("https://gitee.com",)),
    TianhuIconRule(("ip138",), "www.itdog.cn_favicon.ico", ("https://www.ip138.com",)),
    TianhuIconRule(("chinaz",), "domainbeian.ico", ("https://www.chinaz.com",)),
    TianhuIconRule(("adworld", "i春秋"), "adworld.xctf.org.cn_favicon.ico", ("https://adworld.xctf.org.cn",)),
    TianhuIconRule(("tryhackme",), "tryhackme.com_favicon.ico", ("https://tryhackme.com",)),
    TianhuIconRule(("hackthebox",), "hackthebox.png", ("https://www.hackthebox.com",)),
    TianhuIconRule(("vulnhub",), "vulnhub.png", ("https://www.vulnhub.com",)),
    TianhuIconRule(("root-me", "rootme"), "www.root-me.org_favicon.ico", ("https://www.root-me.org",)),
    TianhuIconRule(("vulfocus",), "vulfocus.cn_favicon.ico", ("https://vulfocus.cn",)),
    TianhuIconRule(("0.zone", "零零信安"), "new_default_icon_2.ico", ("https://0.zone",)),
    TianhuIconRule(("threatbook", "微步"), "x.threatbook.com_favicon.ico", ("https://x.threatbook.com",)),
    TianhuIconRule(("aiqicha", "爱企查"), "aiqicha_2.ico", ("https://aiqicha.baidu.com",)),
    TianhuIconRule(("qcc", "企查查"), "qixin.png", ("https://www.qcc.com",)),
    TianhuIconRule(("tianyancha", "天眼查"), "www.tianyancha.com_favicon.ico", ("https://www.tianyancha.com",)),
    TianhuIconRule(("freebuf",), "black-github.png", ("https://www.freebuf.com",)),
    TianhuIconRule(("apifox",), "Apifox_icon.png", ("https://www.apifox.cn",)),
    TianhuIconRule(("reqable",), "cloud_mobile.svg", ("https://reqable.com",)),
    TianhuIconRule(("finalshell",), "lock.svg", ("https://www.hostbuf.com",)),
    TianhuIconRule(("everything",), "new_default_icon_2.ico", ("https://www.voidtools.com",)),
    TianhuIconRule(("deepseek",), "tianhu_import.svg", ("https://www.deepseek.com",)),
    TianhuIconRule(("vscode", "vs code"), "VS Code_icon.png", ("https://code.visualstudio.com",)),
    TianhuIconRule(("pycharm",), "Pycharm_icon.png", ("https://www.jetbrains.com/pycharm/",)),
    TianhuIconRule(("goland",), "Goland_icon.png", ("https://www.jetbrains.com/go/",)),
    TianhuIconRule(("webstorm",), "WebStorm_icon.png", ("https://www.jetbrains.com/webstorm/",)),
    TianhuIconRule(("phpstorm",), "PhpStorm2025.1.1_icon.png", ("https://www.jetbrains.com/phpstorm/",)),
)


def _build_search_text(raw_tool) -> str:
    if not isinstance(raw_tool, dict):
        return ""

    fields = (
        raw_tool.get("name", ""),
        raw_tool.get("description", ""),
        raw_tool.get("category", ""),
        raw_tool.get("group", ""),
        raw_tool.get("type", ""),
        raw_tool.get("url", ""),
        raw_tool.get("path", ""),
        raw_tool.get("tags", ""),
    )
    return " ".join(str(field or "").strip() for field in fields).casefold()


def iter_tianhu_icon_names(raw_tool):
    search_text = _build_search_text(raw_tool)
    if not search_text:
        return

    seen = set()
    for rule in TIANHU_ICON_RULES:
        if any(alias and alias.casefold() in search_text for alias in rule.aliases):
            icon_name = str(rule.icon or "").strip()
            if icon_name and icon_name not in seen:
                seen.add(icon_name)
                yield icon_name


def iter_tianhu_icon_source_urls(raw_tool):
    if not isinstance(raw_tool, dict):
        return

    seen = set()
    raw_url = str(raw_tool.get("url", "") or "").strip()
    if raw_url and raw_url not in seen:
        seen.add(raw_url)
        yield raw_url

    search_text = _build_search_text(raw_tool)
    if not search_text:
        return

    for rule in TIANHU_ICON_RULES:
        if not any(alias and alias.casefold() in search_text for alias in rule.aliases):
            continue
        for source_url in rule.source_urls:
            normalized = str(source_url or "").strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                yield normalized


def build_tianhu_icon_search_url(tool_name: str) -> str:
    text = str(tool_name or "").strip()
    if not text:
        return ""
    return f"https://duckduckgo.com/html/?q={quote_plus(text + ' official site icon')}"
