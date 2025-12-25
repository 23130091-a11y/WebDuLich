@echo off
set PGPASSWORD=123
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE travel_db;"
echo Database created!
pause
