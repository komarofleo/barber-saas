#!/usr/bin/env python3
import os
import subprocess
import datetime
from pathlib import Path

def run_command(cmd, check=True):
    """Выполнить команду и вернуть результат"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout.strip(), e.stderr.strip(), e.returncode

# Создаем директорию
backup_dir = Path("/opt/backups")
backup_dir.mkdir(parents=True, exist_ok=True)

backup_date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = backup_dir / f"backup_log_{backup_date}.txt"

with open(log_file, "w") as log:
    log.write(f"=== Создание бекапа ===\n")
    log.write(f"Дата: {datetime.datetime.now()}\n\n")
    
    # 1. Бекап БД
    log.write("1. Создание бекапа базы данных...\n")
    db_file = backup_dir / f"database_{backup_date}.sql"
    stdout, stderr, code = run_command(
        f"cd /opt/avtoservis && docker compose exec -T postgres pg_dump -U autoservice_user autoservice_db > {db_file}",
        check=False
    )
    if db_file.exists():
        size = db_file.stat().st_size / 1024 / 1024
        log.write(f"   ✓ База данных: {size:.2f} MB\n")
    else:
        log.write(f"   ✗ Ошибка: {stderr}\n")
    
    # 2. Бекап файлов
    log.write("2. Создание бекапа файлов...\n")
    files_file = backup_dir / f"files_{backup_date}.tar.gz"
    stdout, stderr, code = run_command(
        f"cd /opt/avtoservis && tar -czf {files_file} "
        f"--exclude='node_modules' --exclude='.git' --exclude='__pycache__' "
        f"--exclude='*.pyc' --exclude='.env' --exclude='*.log' --exclude='backups' .",
        check=False
    )
    if files_file.exists():
        size = files_file.stat().st_size / 1024 / 1024
        log.write(f"   ✓ Файлы: {size:.2f} MB\n")
    else:
        log.write(f"   ✗ Ошибка: {stderr}\n")
    
    # 3. Итоговый архив
    log.write("3. Создание итогового архива...\n")
    if db_file.exists() and files_file.exists():
        final_file = backup_dir / f"backup_{backup_date}.tar.gz"
        stdout, stderr, code = run_command(
            f"cd {backup_dir} && tar -czf {final_file} {db_file.name} {files_file.name}",
            check=False
        )
        if final_file.exists():
            size = final_file.stat().st_size / 1024 / 1024
            log.write(f"   ✓ Итоговый архив: {size:.2f} MB\n")
            log.write(f"   Файл: {final_file}\n")
        else:
            log.write(f"   ✗ Ошибка: {stderr}\n")
    
    # 4. Проверка sto1
    log.write("4. Поиск sto1...\n")
    for path in ["/mnt/sto1", "/backup/sto1", "/storage/sto1", "/sto1", "/mnt/backup/sto1", "/backup", "/mnt/backup"]:
        if Path(path).exists() and os.access(path, os.W_OK):
            if final_file.exists():
                stdout, stderr, code = run_command(f"cp {final_file} {path}/", check=False)
                if code == 0:
                    log.write(f"   ✓ Скопировано на sto1: {path}\n")
                    break
            else:
                log.write(f"   ⚠ sto1 найден, но бекап не создан\n")
                break
    else:
        log.write("   ⚠ sto1 не найден\n")
    
    # 5. Статистика
    log.write("\n=== Статистика ===\n")
    backups = list(backup_dir.glob("backup_*.tar.gz"))
    if backups:
        latest = max(backups, key=lambda p: p.stat().st_mtime)
        log.write(f"Последний бекап: {latest.name}\n")
        log.write(f"Размер: {latest.stat().st_size / 1024 / 1024:.2f} MB\n")
        log.write(f"Всего бекапов: {len(backups)}\n")
    else:
        log.write("Бекапы не найдены\n")
    
    log.write(f"\n=== Готово ===\n")

# Выводим результат
if log_file.exists():
    print(log_file.read_text())



