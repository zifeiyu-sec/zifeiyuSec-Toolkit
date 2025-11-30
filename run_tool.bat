@echo off
REM 子非鱼工具箱启动脚本
REM 双击运行此脚本，将在隐藏终端中启动工具

REM 使用VBScript隐藏窗口运行Python脚本
set "vbs_file=%temp%\run_tool_temp.vbs"
echo Set WshShell = CreateObject("WScript.Shell") > "%vbs_file%"
echo WshShell.Run "python main.py", 0, False >> "%vbs_file%"

REM 运行VBScript并删除临时文件
cscript //nologo "%vbs_file%"
del "%vbs_file%" >nul 2>&1
