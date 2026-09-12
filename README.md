# DSR ENERGY x CURRENCY CASE STUDY

DS / ML project. Emphasis on API maintenance and ETL, Exploratory Data Analysis and and Machine Learning Prediction.

QUESTION: To what extent does trilateral energy equity (Electricity and Solar Energy) forecast currency stability by 2030?

Dataset: API driven UNComtrade data, DBNomics

Tech Stack: Python, SQL, NashPy, SKlearn, Stats Model (data cleaning, intro / intermediate statistics + game theory, ML models)

Contains an ETL pushing API information into a PGSQL database, then performs statistical calculations. Tried Symbolic regression to find the formula. Ended up doing a PCA driven approach.

PCA continued, then Linear Regression with a prediction

Aim:

UNCOMTRADE
     ↓
DBnomics / WBG
     ↓
Python ETL
     ↓
PostgreSQL
     ↓
Analytical Engine
     ↓
 ┌───┴────────┐
 ↓            ↓
Statistics   ML
 ↓            ↓
 └────┬───────┘
      ↓
Scenario / Game Theory
      ↓
Plotly / Streamlit
      ↓
Cloudflare Website

Future culmination with a simpler, preceding EDA and Visualisation project into a Clouflare and AWS hostred website via a JSON / API bridge
