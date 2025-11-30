' 子非鱼工具箱启动脚本
' 双击运行此脚本，将在隐藏终端中启动工具

Set WshShell = CreateObject("WScript.Shell")
' 运行python main.py，隐藏窗口（第2个参数0表示隐藏窗口）
WshShell.Run "python main.py", 0, False
