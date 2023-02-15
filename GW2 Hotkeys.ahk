#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

#IfWinActive Guild Wars 2
^MButton::
Loop, 6
{
    MouseClick, Left,,, 2
    sleep, 5001
}

#IfWinActive Guild Wars 2
^RButton::
While GetKeyState("RButton", "P")
{
    MouseClick, Left,,, 2
    delay := delay(1,10)
    Sleep %delay%
}
return

delay(cpsmin, cpsmax)
{
    Random, number, cpsmin, cpsmax
    delay := 1000/number
    return, %delay%
}