# Always launches uvicorn with this project's venv interpreter, regardless
# of whether the venv happens to be activated in the calling shell — avoids
# the "system Python picked up instead of venv -> ImportError: cannot
# import name 'genai' from 'google'" failure (see readme.md Known
# Limitations and INTERVIEW_PREP.md problem #10).
Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
& ".\venv\Scripts\python.exe" -m uvicorn app.main:app --reload
