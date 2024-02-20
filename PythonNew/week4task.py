# from flask import Flask, render_template, request
# from langchain.llms import OpenAI
# import tiktoken
# from langchain_community.llms import OpenAI
# from flask import jsonify
# from textblob import TextBlob


# app = Flask(__name__)

# past_responses = {}

# @app.route('/')
# def index():
#     return render_template('index.html', past_responses=past_responses.items())

# def count_tokens(string: str) -> int:
#     # Load the encoding for gpt-3.5-turbo (which uses cl100k_base)
#     encoding_name = "p50k_base"
#     encoding = tiktoken.get_encoding(encoding_name) 
#     # Encode the input string and count the tokens
#     num_tokens = len(encoding.encode(string))
#     return num_tokens

# def generate_response(input_text, openai_api_key):
#     try:
#         llm = OpenAI(temperature=0.7, openai_api_key=openai_api_key)
#         response = llm(input_text)
#         num_tokens = count_tokens(input_text)
#         return f"Input contains {num_tokens} tokens.", response
#     except Exception as e:
#         return "An error occurred:", str(e)

# @app.route('/process', methods=['POST'])
# def process():
#     openai_api_key = request.form['openai_api_key']
#     input_text = request.form['input_text']
#     if not openai_api_key.startswith('sk-'):
#         return "Please enter your OpenAI API key!"
#     else:
#         info, response = generate_response(input_text, openai_api_key)
#         past_responses[input_text] = response  # Store the current query and response
#         return f"{info}\n{response}"

# @app.route('/get_past_responses', methods=['GET'])
# def get_past_responses():
#     # Logic to retrieve past responses from past_responses dictionary or your database
#     # For example, assuming past_responses is a dictionary containing past queries and responses
#     # You can replace this logic with your actual implementation
#     past_responses_list = [{'query': query, 'response': response} for query, response in past_responses.items()]
#     return jsonify(past_responses_list)

# if __name__ == '__main__':
#     app.run(debug=True)


from flask import Flask, render_template, request, jsonify, g
from langchain.llms import OpenAI
import tiktoken
from langchain_community.llms import OpenAI
from textblob import TextBlob
import sqlite3

app = Flask(__name__)

# Initialize LangChain
openai_api_key = "YOUR_OPENAI_API_KEY"
llm = OpenAI(openai_api_key=openai_api_key)

# Configuration
DATABASE = 'conversations.db'

# Create connection to database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

# Initialize database if necessary
def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS responses (
                            id INTEGER PRIMARY KEY,
                            query TEXT,
                            response TEXT,
                            sentiment TEXT
                        )''')
        db.commit()

# Close database connection after each request
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

past_responses = {}

@app.route('/')
def index():
    return render_template('index.html', past_responses=past_responses.items())

def count_tokens(string: str) -> int:
    # Load the encoding for gpt-3.5-turbo (which uses cl100k_base)
    encoding_name = "p50k_base"
    encoding = tiktoken.get_encoding(encoding_name) 
    # Encode the input string and count the tokens
    num_tokens = len(encoding.encode(string))
    return num_tokens

def generate_response(input_text, openai_api_key):
    try:
        llm = OpenAI(temperature=0.7, openai_api_key=openai_api_key)
        response = llm(input_text)
        num_tokens = count_tokens(input_text)
        sentiment = perform_sentiment_analysis(response)
        return f"Input contains {num_tokens} tokens.", response, sentiment
    except Exception as e:
        return "An error occurred:", str(e), None

def perform_sentiment_analysis(response):
    blob = TextBlob(response)
    sentiment_score = blob.sentiment.polarity
    if sentiment_score > 0:
        return "Positive"
    elif sentiment_score < 0:
        return "Negative"
    else:
        return "Neutral"

def store_response(query, response, sentiment):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO responses (query, response, sentiment) VALUES (?, ?, ?)", (query, response, sentiment))
    db.commit()

@app.route('/process', methods=['POST'])
def process():
    openai_api_key = request.form['openai_api_key']
    input_text = request.form['input_text']
    if not openai_api_key.startswith('sk-'):
        return "Please enter your OpenAI API key!"
    else:
        info, response, sentiment = generate_response(input_text, openai_api_key)
        past_responses[input_text] = {'response': response, 'sentiment': sentiment}  # Store the current query, response, and sentiment
        store_response(input_text, response, sentiment)  # Store the response in the database
        return f"{info}\n{response}\nSentiment: {sentiment}"

@app.route('/get_past_responses', methods=['GET'])
def get_past_responses():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM responses")
    responses = cursor.fetchall()
    past_responses_list = [{'query': response[1], 'response': response[2], 'sentiment': response[3]} for response in responses]
    return jsonify(past_responses_list)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)