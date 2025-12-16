' SubFeiYu Toolbox Launch Script
' Directly start the application without creating desktop shortcut

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get script path and directory
scriptPath = WScript.ScriptFullName
scriptDir = fso.GetParentFolderName(scriptPath)
mainScript = fso.BuildPath(scriptDir, "main.py")

' Check if main.py exists
If Not fso.FileExists(mainScript) Then
    MsgBox "Error: main.py not found", vbCritical, "Launch Error"
    WScript.Quit 1
End If

' Try different Python commands
On Error Resume Next

' Try pythonw (no console window)
WshShell.Run "pythonw """ & mainScript & """", 0, False
If Err.Number = 0 Then
    WScript.Quit 0
End If
Err.Clear

' Try python
WshShell.Run "python """ & mainScript & """", 0, False
If Err.Number = 0 Then
    WScript.Quit 0
End If
Err.Clear

' Try python3
WshShell.Run "python3 """ & mainScript & """", 0, False
If Err.Number = 0 Then
    WScript.Quit 0
End If
Err.Clear

' Try py
WshShell.Run "py """ & mainScript & """", 0, False
If Err.Number = 0 Then
    WScript.Quit 0
End If
Err.Clear

' If all commands fail, show error message
MsgBox "Failed to start application. Please ensure:" & vbCrLf & "1. Python is installed" & vbCrLf & "2. Python is in PATH" & vbCrLf & "3. All dependencies are installed", vbCritical, "Launch Error"
WScript.Quit 1