# Document and Database Query System for Enhanced User Interaction
## Description
- This project involves the development of a sophisticated chatbot capable of seamlessly handling both document management and database querying powered by GPT-4o to improve user experience at the request of SAUGO 360.
- The system also integrates advanced natural language processing capabilities, allowing the chatbot to understand and respond to user queries about a certain database. The chatbot can generate and execute SQL queries, fetch relevant data, and even create various types of visualizations such as line charts, bar charts, pie charts, and heatmaps.
- The system supports location-based queries, providing maps and triangular area visualizations based on user input.
- Users can also upload PDF documents via a user-friendly interface, and ask questions about them.
> [!IMPORTANT]
> This repository contains the backend portion of the chatbot only. For a complete experience, please navigate to https://github.com/SAUGO360-Internship-Project/FrontEnd_Chatbot.git to setup the frontend and follow the instructions.

> [!WARNING]
> This chatbot may make mistakes.
## Table of Contents
- Installation and Setup
- Usage
- Credits
## Installation and Setup
1. Start by cloning the repository using the following link: `https://github.com/SAUGO360-Internship-Project/BackEnd_ChatBot.git`, and pasting it in your preferred IDE.
2. Navigate to the Project Directory: *example:* `cd backend\BackEnd_ChatBot`
3. Create a virtual environemnt using: `py -3 -m venv venv`
4. Activate your virtual environment with the following command: `venv\Scripts\activate`
5. Execute the following to install the required libraries: `pip install -r requirements.txt`
6. Create your `.env` file in the main directory, it should include:
```
OPENAI_API_KEY= YOUR-OPENAI-KEY
DB_CONFIG = 'A link to a PostgreSQL database to store the required models'
DB_CONFIG_TEST = 'A link to the PostgreSQL database that contains the tables that you will be asking questions about'
SECRET_KEY = "b'|\xe7\xbfU3`\xc4\xec\xa7\xa9zf:}\xb5\xc7\xb9\x139^3@Dv'"
GOOGLE_MAPS_API_KEY= YOUR-GOOGLE-MAPS-API-KEY
```
7. Initialize the database using:
```
flask db init -d migrations
flask db migrate -d migrations
flask db upgrade -d migrations
```
8. Run the backend using: `python -m flask --app app.py --debug run`
## Usage 
- After running the frontend, you will now be able to access the full functionalities of this chatbot.
- You can ask questions about the database of interest, and ask for visualizations including: **LineChart, BarChart, PieChart, Maps, PolygonMaps, HeatMap**.
- The chatbot will not retrieve any sensitive content and will not answer any irrelevant questions.
- The user may also upload PDF documents and ask questions about them. The chatbot will know whether the user is asking about the database or the PDF documents.
## Credits
- Developed by Saadeddine Yassine and Ihab Faour
- SAUGO 360
- Contributors: Moussa Waked and Hussein Ibrahim 
