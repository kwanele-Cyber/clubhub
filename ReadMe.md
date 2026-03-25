# How to run the application

1. install the environment
```bash
python -m venv clubhub-venv
```

2. open the environment 

## on windows

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass 
./clubhub-venv/Scripts/Activate.ps1
```

## on linux

```bash
source ./clubhub-venv/Bin/activate
```

4. Install pip packages

```bash
pip install -r requirements.txt
```

5. init the database

```bash
python init_db.py
```

6. run the app

```bash
python run.py
```

