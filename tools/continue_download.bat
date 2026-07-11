@echo off
chcp 65001 >nul
echo ============================================
echo 1000首歌曲批量下载 - 从断点继续
echo ============================================
echo.
echo 当前已下载歌曲会自动跳过
echo 按 Ctrl+C 可随时停止，下次运行继续
echo.
cd /d D:\video-grap
python tools\download_all_1000.py
echo.
echo ============================================
echo 下载完成！检查报告：
echo D:\video-grap\Downloaded\music_batch\_full_report.json
echo ============================================
pause
