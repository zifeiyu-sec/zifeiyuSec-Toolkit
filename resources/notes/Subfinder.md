> httpx -l domains.txt -nf -sc -mc 200,403 -silent -o alive_gipc.txt
同时探测 HTTP (80) 和 HTTPS (443)，不做协议回退，两个协议只要符合条件就都输出
正则只保留url
^(https?:\/\/[^\s]+)\s+\[.*\]$
$1

