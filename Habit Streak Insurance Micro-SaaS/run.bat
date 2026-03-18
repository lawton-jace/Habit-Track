@echo off
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting Habit Streak Insurance...
echo Open http://localhost:5000 in your browser
echo.
python app.py
