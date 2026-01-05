#!/bin/bash

echo "=== Проверка бекапа ===" > /tmp/backup_check_result.txt
date >> /tmp/backup_check_result.txt
echo "" >> /tmp/backup_check_result.txt

# Проверка директории
if [ -d /opt/backups ]; then
    echo "✓ Директория /opt/backups существует" >> /tmp/backup_check_result.txt
else
    echo "✗ Директория /opt/backups не существует" >> /tmp/backup_check_result.txt
    exit 1
fi

# Проверка бекапов
echo "Проверка файлов бекапа:" >> /tmp/backup_check_result.txt
ls -lh /opt/backups/backup_*.tar.gz 2>/dev/null >> /tmp/backup_check_result.txt || echo "Нет файлов backup_*.tar.gz" >> /tmp/backup_check_result.txt
echo "" >> /tmp/backup_check_result.txt

# Последний бекап
LAST_BACKUP=$(ls -t /opt/backups/backup_*.tar.gz 2>/dev/null | head -1)
if [ -n "$LAST_BACKUP" ]; then
    echo "✓ Последний бекап: $LAST_BACKUP" >> /tmp/backup_check_result.txt
    ls -lh "$LAST_BACKUP" >> /tmp/backup_check_result.txt
    echo "" >> /tmp/backup_check_result.txt
    echo "Размер: $(du -h "$LAST_BACKUP" | cut -f1)" >> /tmp/backup_check_result.txt
    echo "Дата создания: $(stat -c %y "$LAST_BACKUP" 2>/dev/null || stat -f %Sm "$LAST_BACKUP" 2>/dev/null)" >> /tmp/backup_check_result.txt
else
    echo "✗ Бекап не найден" >> /tmp/backup_check_result.txt
fi

echo "" >> /tmp/backup_check_result.txt
echo "Всего бекапов: $(ls -1 /opt/backups/backup_*.tar.gz 2>/dev/null | wc -l)" >> /tmp/backup_check_result.txt
echo "Общий размер: $(du -sh /opt/backups 2>/dev/null | cut -f1)" >> /tmp/backup_check_result.txt

# Проверка на sto1
echo "" >> /tmp/backup_check_result.txt
echo "Проверка sto1:" >> /tmp/backup_check_result.txt
STO1_BACKUP=$(find /mnt /backup /storage /sto1 -maxdepth 3 -name "backup_*.tar.gz" -type f 2>/dev/null | head -1)
if [ -n "$STO1_BACKUP" ]; then
    echo "✓ Найден на sto1: $STO1_BACKUP" >> /tmp/backup_check_result.txt
    ls -lh "$STO1_BACKUP" >> /tmp/backup_check_result.txt
else
    echo "⚠ Не найден на sto1" >> /tmp/backup_check_result.txt
fi

echo "" >> /tmp/backup_check_result.txt
echo "=== Готово ===" >> /tmp/backup_check_result.txt

cat /tmp/backup_check_result.txt



