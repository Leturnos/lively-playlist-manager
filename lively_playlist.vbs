Set WinScriptHost = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

' Use the pythonw.exe from the uv-managed .venv
' We assume 'uv sync' has been run to create the .venv
pythonPath = strPath & "\.venv\Scripts\pythonw.exe"
scriptPath = strPath & "\src\main.pyw"

' Run with parameter 0 to hide console window
WinScriptHost.Run Chr(34) & pythonPath & Chr(34) & " " & Chr(34) & scriptPath & Chr(34), 0
Set WinScriptHost = Nothing