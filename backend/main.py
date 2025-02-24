from fastapi import FastAPI
import requests
import openai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Load API Keys & Salesforce Credentials
SALESFORCE_DOMAIN = os.getenv("SALESFORCE_DOMAIN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Authenticate with Salesforce
def authenticate_salesforce():
    token_url = f"https://{SALESFORCE_DOMAIN}.salesforce.com/services/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "username": USERNAME,
        "password": PASSWORD
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=payload, headers=headers)
    return response.json().get("access_token"), response.json().get("instance_url")

ACCESS_TOKEN, INSTANCE_URL = authenticate_salesforce()

# Get Sales Profile Users
@app.get("/users")
def get_users():
    query = "SELECT Id, Name FROM User WHERE Profile.Name = 'Account Executive'"
    query_url = f"{INSTANCE_URL}/services/data/v60.0/query/?q={query}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    response = requests.get(query_url, headers=headers)
    return response.json().get("records", [])

# Get Open Opportunities for Selected User
@app.get("/opportunities/open")
def get_open_opportunities(user_id: str):
    query = f"SELECT Id, Name, Amount, StageName, CloseDate FROM Opportunity WHERE IsClosed = FALSE AND OwnerId = '{user_id}'"
    query_url = f"{INSTANCE_URL}/services/data/v60.0/query/?q={query}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    response = requests.get(query_url, headers=headers)
    return response.json().get("records", [])

# Summarize Opportunity
@app.get("/opportunities/summarize")
def summarize_opportunity(opportunity_id: str):
    query = f"SELECT Id, Name, Amount, StageName, CloseDate FROM Opportunity WHERE Id = '{opportunity_id}'"
    query_url = f"{INSTANCE_URL}/services/data/v60.0/query/?q={query}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    response = requests.get(query_url, headers=headers)
    opportunity = response.json().get("records", [])

    if not opportunity:
        return {"error": "Opportunity not found"}

    data_for_ai = f"""
    Opportunity: {opportunity[0]['Name']}
    Amount: {opportunity[0].get('Amount', 'N/A')}
    Stage: {opportunity[0]['StageName']}
    Close Date: {opportunity[0]['CloseDate']}
    """

    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"Summarize this sales opportunity:\n{data_for_ai}"
    
    ai_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {"summary": ai_response.choices[0].message.content}
