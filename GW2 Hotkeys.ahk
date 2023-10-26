#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.

#IfWinActive Guild Wars 2
^Numpad8::
Loop, 2
{
    xfudge1 := 1010 + fudgefactor(1, 40)
    yfudge1 := 710 + fudgefactor(1, 10)
    delayfudge1 := 50 + fudgefactor(9, 31)
    mousemove, %xfudge1%, %yfudge1%
    MouseClick, left
    Sleep, %delayfudge1%

    xfudge2 := 1122 + fudgefactor(1, 35)
    yfudge2 := 701 + fudgefactor(1, 17)
    delayfudge2 := 2000 + fudgefactor(17, 163)
    mousemove, %xfudge2%, %yfudge2%
    MouseClick, left
    Sleep, %delayfudge2%
}
return

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

fudgefactor(cmin, cmax)
{
    Random, number, cmin, cmax
    return, number
}