' Launch watchdog.ps1 with NO console window (task scheduler friendly).
' Usage: wscript.exe //nologo watchdog_hidden.vbs [McpPort] [DemoPort]
' Why: a scheduled task that runs powershell.exe directly flashes a console
' window every time it fires. WScript.Shell.Run with window style 0 avoids it.
Option Explicit

Dim sh, fso, here, ps, mcp, demo
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

here = fso.GetParentFolderName(WScript.ScriptFullName)
mcp  = "9700"
demo = "9701"
If WScript.Arguments.Count >= 1 Then mcp  = WScript.Arguments(0)
If WScript.Arguments.Count >= 2 Then demo = WScript.Arguments(1)

ps = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & here & "\watchdog.ps1""" & _
     " -McpPort " & mcp & " -DemoPort " & demo

' 0 = hidden, False = do not wait
sh.Run ps, 0, False
