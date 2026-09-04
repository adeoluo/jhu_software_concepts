Johns Hopkins University - Modern Software Concepts in Python
Module 1 - Personal Website

This project is a personal developer website built with Flask.

Prerequisites
- Python 3.10 or newer
- Git
- A web browser, such as Safari, Chrome, or Firefox

Setup and Run Instructions
1. Open Terminal and go to the folder where you want to store the repository.
2. Clone the repository:
   git clone git@github.com:adeoluo/jhu_software_concepts.git
3. Enter the Module 1 folder:
   cd jhu_software_concepts/module_1
4. Create and activate a virtual environment:
   python3 -m venv .venv
   source .venv/bin/activate
5. Install dependencies:
   python -m pip install -r requirements.txt
6. Start the website:
   python run.py
7. Open http://localhost:8080 in a browser.

Troubleshooting

Python command not found:
Activate the virtual environment, then run:
   source .venv/bin/activate
   python run.py

Flask module not found:
Activate the virtual environment and install dependencies:
   source .venv/bin/activate
   python -m pip install -r requirements.txt

Port 8080 already in use:
Stop the terminal window that is already running Flask with Control+C, then run:
   python run.py

Stopping the website:
Return to the terminal running Flask and press Control+C.
