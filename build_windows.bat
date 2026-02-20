@echo off
echo ====================================================
echo   大學申請入學分則統整系統 - Windows 打包腳本
echo ====================================================

echo [1/3] 正在安裝或升級必備套件...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [2/3] 正在執行 PyInstaller 打包...
REM 注意：Windows 下 add-data 必須使用分號 (;) 而不是冒號 (:)
pyinstaller --name "CAC_Scraper" --windowed --add-data "templates;templates" --add-data "static;static" app.py

echo [3/3] 打包完成！
echo 請至 dist 資料夾下尋找 CAC_Scraper (或 CAC_Scraper.exe)
pause
