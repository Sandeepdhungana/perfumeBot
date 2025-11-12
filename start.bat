@echo off
echo Starting Perfume Chatbot Server...
echo.
echo Make sure you have:
echo 1. Set your OPENAI_API_KEY in .env file
echo 2. Database file 'perfumes.db' exists
echo 3. Installed requirements: pip install -r requirements.txt
echo.
pause
python server.py