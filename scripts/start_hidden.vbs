Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
projectDir = fso.GetParentFolderName(scriptDir)
WshShell.CurrentDirectory = projectDir

' Use venv Python if available, otherwise fall back to system Python
venvPython = projectDir & "\venv\Scripts\pythonw.exe"
If fso.FileExists(venvPython) Then
    WshShell.Run """" & venvPython & """ -u -m talkrefine", 0, False
Else
    WshShell.Run "pythonw -u -m talkrefine", 0, False
End If
