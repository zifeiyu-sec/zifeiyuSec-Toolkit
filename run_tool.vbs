' 子非鱼工具箱启动脚本
' 直接启动应用程序，不创建桌面快捷方式

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptPath = WScript.ScriptFullName
scriptDir = fso.GetParentFolderName(scriptPath)
mainScript = fso.BuildPath(scriptDir, "main.py")

On Error Resume Next
' 使用参数0隐藏窗口，True表示等待命令完成
WshShell.Run "python """ & mainScript & """", 0, True

If Err.Number <> 0 Then
    MsgBox "Error: Could not start the application. Please make sure Python is installed and in your system PATH.", vbCritical, "启动错误"
    WScript.Quit 1
End If

On Error GoTo 0
WScript.Quit 0