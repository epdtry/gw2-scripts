#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.


#IfWinActive Guild Wars 2
^LButton::
MouseClick, left
mousegetpos, x, y
mousemove, 910, 600
sleep, 50
MouseClick, left
sleep, 50
mousemove, %x%, %y%
return