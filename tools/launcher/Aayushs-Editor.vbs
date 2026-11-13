' Runs Aayushs-Editor.ps1 with no console window (the desktop shortcut points here).
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & here & "\Aayushs-Editor.ps1""", 0, False
