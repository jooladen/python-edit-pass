$pyinstaller = "C:\Users\jooladen\anaconda3\envs\pkg\Scripts\pyinstaller.exe"
$tcl    = "C:\Users\jooladen\anaconda3\envs\pkg\Library\lib\tcl8.6"
$tk     = "C:\Users\jooladen\anaconda3\envs\pkg\Library\lib\tk8.6"
$tclDll = "C:\Users\jooladen\anaconda3\envs\pkg\Library\bin\tcl86t.dll"
$tkDll  = "C:\Users\jooladen\anaconda3\envs\pkg\Library\bin\tk86t.dll"

Set-Location $PSScriptRoot
$old = "dist\pdf-unlock.exe"
if (Test-Path $old) { Remove-Item $old -Force }

Write-Host "Building..."
& $pyinstaller --onefile --windowed --name pdf-unlock `
    --add-data "$tcl;tcl8.6" `
    --add-data "$tk;tk8.6" `
    --add-binary "$tclDll;." `
    --add-binary "$tkDll;." `
    remove_password_gui.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS: dist\pdf-unlock.exe"
} else {
    Write-Host "FAILED"
}
Read-Host "Press Enter to exit"
