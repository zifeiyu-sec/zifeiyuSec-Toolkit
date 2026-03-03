afrog 常用命令&参数笔记
 > 使用代理批量扫描
main.exe -T urls.txt -proxy http://127.0.0.1:55558 -o scan_result
.html


一、最常用万能命令（直接复制使用，优先放最前）

# 1. 单目标+高危漏洞+HTML报告+礼貌扫描（最常用）

afrog -t http://xxx -S high -o report.html -polite

# 2. 批量目标（文件）+带Cookie+静默输出

afrog -T target.txt -H "Cookie: xxx" -silent -o result.html

# 3. 指定PoC+调试（排错/写PoC用）

afrog -t http://xxx -P test.poc -debug

# 4. 空间测绘拉取资产+扫描

afrog -cs zoomeye -q "app:'tomcat'" -qc 200 -o report.html

二、高频参数（常用优先，紧凑排版）

### （一）目标指定（必用）

-t 目标        单个/多个目标（URL/IP，逗号分隔）

-T 目标.txt   从文件读取目标（一行一个）

-cs 引擎      空间测绘引擎（如zoomeye）

-q 关键词     测绘查询语句（如app:'tomcat'）

### （二）POC选择（核心）

-P 文件/目录  指定单个PoC或PoC目录

-s 关键词     筛选含指定关键词的PoC（如tomcat）

-S 级别       按风险等级筛选（high/critical最常用）

-pl           列出所有内置PoC

### （三）输出结果（常用）

-o 文件名.html 输出HTML报告（最常用）

-silent       静默模式，只显示漏洞结果（不刷屏）

-ja 文件名.json 输出完整JSON（含请求响应）

### （四）并发速率（防封必调）

-c 数量       并发数（默认25，调小更稳）

-polite       礼貌扫描（慢、稳，不易被封）

-aggressive   激进扫描（快，易被封）

### （五）常用辅助（高频）

-proxy 代理   挂代理（如http://127.0.0.1:7890）

-H "头信息"   自定义请求头/Cookie（如Cookie: xxx）

-debug        调试模式，显示完整请求响应（排错用）

三、低频参数（备用，紧凑略写）

-resume       恢复中断扫描；-nf 关闭指纹识别；-w 开启Web存活探测

-ps -p top    前置常用端口扫描；-un 更新afrog；-v 查看版本

-validate 文件 校验PoC语法；-dingtalk 钉钉推送漏洞
