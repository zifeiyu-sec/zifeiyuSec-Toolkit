Nuclei 常用笔记

一、工具简介

Nuclei：基于模板的快速漏洞扫描工具，可配置性强、易用，适合Web/各类协议漏洞探测。

二、核心常用命令（直接复制可用）

1. 基础扫描

- 单目标全量扫描：nuclei -u https://example.com

- 单目标指定模板：nuclei -u https://example.com -t http/cves/ -t http/xss/

2. 批量扫描（适配alive_gipc.txt）

- 批量静默扫描：nuclei -l alive_gipc.txt -silent

- 批量+排除主机：nuclei -l alive_gipc.txt -eh "127.0.0.1,localhost" -silent

3. 精准筛选

- 只扫高危/严重：nuclei -l alive_gipc.txt -s high,critical -silent

- 只扫Web漏洞：nuclei -l alive_gipc.txt -pt http -silent

- 只扫CVE漏洞：nuclei -l alive_gipc.txt -tags cve -silent

4. 结果导出

- 文本导出：nuclei -l alive_gipc.txt -silent -o nuclei_vulns.txt

- JSONL导出：nuclei -l alive_gipc.txt -jsonl -o nuclei_vulns.jsonl

- Markdown导出：nuclei -l alive_gipc.txt -markdown-export nuclei_report/

5. 进阶优化（适配教育网+常用参数）

常用参数说明（代理、延时等，高频必备）：

- -p, -proxy：使用代理（http/socks5），格式：-p http://127.0.0.1:8080 或 -p socks5://127.0.0.1:1080，用于绕过防护、隐藏本机IP

- -delay：请求间隔（延时），格式：-delay 500ms 或 -delay 1s，避免发包过快触发目标防护（适配脆弱/高校目标）

- -rl, -rate-limit：每秒最大请求数，如 -rl 100，控制发包速率

- -c, -concurrency：并行模板数，如 -c 30，减少目标压力

优化命令示例（整合常用参数）：

- 调整并发速率+延时：nuclei -l alive_gipc.txt -c 30 -rl 100 -delay 500ms -silent

- 超时重试+跟随重定向：nuclei -l alive_gipc.txt -fr -timeout 15 -retries 2 -silent

- 代理+批量扫描：nuclei -l alive_gipc.txt -p http://127.0.0.1:8080 -silent（绕过防护专用）

6. 工具维护

- 更新引擎：nuclei -up

- 更新漏洞模板：nuclei -ut（必做，保证覆盖新漏洞）

三、关键备注

- 常用模板路径：http/cves/（CVE）、http/sql-injection/（SQLi）、http/xss/（XSS）

- severity级别：info（信息）、low（低危）、medium（中危）、high（高危）、critical（严重）

- 核心组合：批量扫描+静默+导出 → nuclei -l alive_gipc.txt -silent -o nuclei_vulns.txt

- 高频参数总结：代理(-p)、延时(-delay)、速率限制(-rl)、并发(-c)，按需组合使用，避免触发目标防护
