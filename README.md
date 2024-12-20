#Cryptix DB Filler

Open in Bat / Powershell File

## Powershell

if (-not (Test-Path -Path .\venv)) {
    python -m venv venv
}

. .\venv\Scripts\Activate

$env:PYTHONPATH = "$env:PYTHONPATH;C:\your-path\cryptix-db-filler-last\cryptixd"

$env:CRYPTIXD_HOST_1 = "127.0.0.1:19201"

$env:SQL_URI = "postgresql+psycopg2://postgres:your-pass@localhost:5432/postgres"

$env:VERSION = "$Version"

python main.py
