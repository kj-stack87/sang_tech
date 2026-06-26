$ErrorActionPreference = "Stop"

$BundledPython = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (Test-Path -LiteralPath $BundledPython) {
    $Python = $BundledPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $Python = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Python = "python"
} else {
    throw "Python 실행 파일을 찾을 수 없습니다. Python 3.11+를 설치한 뒤 다시 실행하세요."
}

& $Python -m pip install -r requirements.txt
