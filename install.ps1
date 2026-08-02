$ErrorActionPreference = "Stop"
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   DomainScout Requirements & Version Checker     " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[X] Error: Git is not installed." -ForegroundColor Red
    exit
}
$PythonCmd = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$DefaultDir = Join-Path (Get-Location).Path "DomainScout"
$InstallDir = Read-Host "Enter installation directory (Leave blank for default: $DefaultDir)"
if ([string]::IsNullOrWhiteSpace($InstallDir)) { $InstallDir = $DefaultDir }

if (Test-Path $InstallDir) {
    Set-Location $InstallDir
    if (Test-Path ".git") {
        Write-Host "[!] DomainScout folder already exists. Checking for updates..." -ForegroundColor Yellow
        git pull origin main
    } else {
        Set-Location (Split-Path $InstallDir -Parent)
        Start-Sleep -Seconds 1
        $FolderContents = Get-ChildItem -Path $InstallDir -Force
        if ($FolderContents.Count -eq 0) {
            Write-Host "[!] Folder exists but is empty. Cleaning up and cloning repository..." -ForegroundColor Yellow
            cmd /c rmdir /s /q "$InstallDir"
            git clone https://github.com/codekere/domain-scout.git $InstallDir
            Set-Location $InstallDir
        } else {
            Write-Host "[X] CRITICAL ERROR: Target directory '$InstallDir' is not empty and not a valid repository." -ForegroundColor Red
            exit
        }
    }
} else {
    Write-Host "[!] Cloning DomainScout repository..." -ForegroundColor Yellow
    git clone https://github.com/codekere/domain-scout.git $InstallDir
    Set-Location $InstallDir
}

if (-not (Test-Path "code.py")) {
    Write-Host "`n[X] CRITICAL ERROR: Core file 'code.py' is missing!" -ForegroundColor Red
    exit
}

Write-Host "`n[*] Analyzing installed requirements and versions..." -ForegroundColor Cyan
if (Test-Path "requirements.txt") {
    $reqs = Get-Content "requirements.txt" | Where-Object { $_ -match '^\s*[^#]' }
    $hasOutdatedOrMissing = $false

    foreach ($req in $reqs) {
        if ($req -match '^\s*([a-zA-Z0-9\-_]+)\s*(?:==|>=|<=)?\s*(.*)?\s*$') {
            $pkgName = $Matches[1].Trim()
            $reqVersion = $Matches[2].Trim()
            
            $pyCheckCode = "import importlib.metadata as m; 
try: print(m.version('$pkgName'))
except: print('NOT_INSTALLED')"
            
            $instVersion = (& $PythonCmd -c "$pyCheckCode").Trim()
            
            if ($instVersion -eq "NOT_INSTALLED") {
                Write-Host " • $pkgName : [MISSING]" -ForegroundColor Red
                $hasOutdatedOrMissing = $true
            } else {
                if ($reqVersion -and $instVersion -lt $reqVersion) {
                    Write-Host " • $pkgName : [LOWER VERSION] (Installed: $instVersion | Required: $reqVersion)" -ForegroundColor Yellow
                    $hasOutdatedOrMissing = $true
                } else {
                    Write-Host " • $pkgName : [OK] (Installed: $instVersion)" -ForegroundColor Green
                }
            }
        }
    }

    if ($hasOutdatedOrMissing) {
        Write-Host "`n[!] Some requirements are missing or have a lower version than required." -ForegroundColor Yellow
        $updateChoice = Read-Host "Would you like to update/install them now? (Y/N)"
        if ($updateChoice -eq 'Y' -or $updateChoice -eq 'y') {
            Write-Host "[*] Updating and installing modules..." -ForegroundColor Cyan
            & $PythonCmd -m pip install -r requirements.txt
            Write-Host "[✓] Successfully updated all requirements!" -ForegroundColor Green
        } else {
            Write-Host "[!] Update process skipped by user." -ForegroundColor Yellow
        }
    } else {
        Write-Host "`n[✓] All requirements are fully satisfied and up-to-date!" -ForegroundColor Green
    }
} else {
    Write-Host "[!] requirements.txt not found." -ForegroundColor Yellow
}

$ShortcutPath = "$([Environment]::GetFolderPath('Desktop'))\Domain Scout.lnk"
$WScriptShell = New-Object -ComObject WScript.Shell

if (Test-Path $ShortcutPath) {
    Write-Host "`n[✓] Desktop shortcut already exists. Verifying and updating properties..." -ForegroundColor Green
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "$PythonCmd"
    $Shortcut.Arguments = "code.py"
    $Shortcut.WorkingDirectory = $InstallDir
    
    $LogoIco = Join-Path $InstallDir "assets\logo.ico"
    if (Test-Path $LogoIco) {
        $Shortcut.IconLocation = "$LogoIco, 0"
    }
    $Shortcut.Save()
    Write-Host "[✓] Shortcut properties successfully verified & updated!" -ForegroundColor Green
} else {
    $createShortcut = Read-Host "`nDo you want to create a Desktop shortcut with logo? (Y/N)"
    if ($createShortcut -eq 'Y' -or $createShortcut -eq 'y') {
        $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
        $Shortcut.TargetPath = "$PythonCmd"
        $Shortcut.Arguments = "code.py"
        $Shortcut.WorkingDirectory = $InstallDir
        
        $LogoIco = Join-Path $InstallDir "logo.ico"
        if (Test-Path $LogoIco) {
            $Shortcut.IconLocation = "$LogoIco, 0"
            Write-Host "[✓] Custom logo.ico applied to shortcut!" -ForegroundColor Green
        } else {
            Write-Host "[!] Note: logo.ico not found in folder. Shortcut created without custom icon." -ForegroundColor Yellow
        }
        
        $Shortcut.Save()
        Write-Host "[✓] Desktop shortcut 'Domain Scout' created successfully!" -ForegroundColor Green
    }
}

Write-Host "`n[✓] Setup process finished! Launching DomainScout..." -ForegroundColor Green
& $PythonCmd code.py
