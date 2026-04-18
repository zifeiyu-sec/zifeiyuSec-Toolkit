' ZifeiyuSec source launcher
' Launch the toolbox the same way as: python main.py

Option Explicit

Dim WshShell, fso
Dim scriptPath, scriptDir, mainScript
Dim localPythonw, localPython

Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptPath = WScript.ScriptFullName
scriptDir = fso.GetParentFolderName(scriptPath)
mainScript = fso.BuildPath(scriptDir, "main.py")
localPythonw = fso.BuildPath(fso.BuildPath(scriptDir, ".venv\Scripts"), "pythonw.exe")
localPython = fso.BuildPath(fso.BuildPath(scriptDir, ".venv\Scripts"), "python.exe")

If Not fso.FileExists(mainScript) Then
    MsgBox "Error: main.py not found", vbCritical, "Launch Error"
    WScript.Quit 1
End If

WshShell.CurrentDirectory = scriptDir

If fso.FileExists(localPythonw) Then
    WshShell.Run """" & localPythonw & """ """ & mainScript & """", 0, False
    WScript.Quit 0
End If

If fso.FileExists(localPython) Then
    WshShell.Run """" & localPython & """ """ & mainScript & """", 0, False
    WScript.Quit 0
End If

On Error Resume Next

WshShell.Run "pythonw """ & mainScript & """", 0, False
If Err.Number = 0 Then
    WScript.Quit 0
End If
Err.Clear

WshShell.Run "python """ & mainScript & """", 0, False
If Err.Number = 0 Then
    WScript.Quit 0
End If
Err.Clear

WshShell.Run "pyw """ & mainScript & """", 0, False
If Err.Number = 0 Then
    WScript.Quit 0
End If
Err.Clear

WshShell.Run "py """ & mainScript & """", 0, False
If Err.Number = 0 Then
    WScript.Quit 0
End If
Err.Clear

MsgBox "Failed to start application. Please ensure:" & vbCrLf & _
       "1. Python is installed" & vbCrLf & _
       "2. Dependencies are installed" & vbCrLf & _
       "3. The project can run with 'python main.py'", _
       vbCritical, "Launch Error"
WScript.Quit 1
