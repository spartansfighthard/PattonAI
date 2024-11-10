from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI

def handle_cors(response):
    response.update({
        "headers": {
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS,PATCH,DELETE,POST,PUT",
            "Access-Control-Allow-Headers": "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version"
        }
    })
    return response

def handler(request):
    # Handle CORS preflight request
    if request.method == "OPTIONS":
        return handle_cors({
            "statusCode": 200,
            "body": ""
        })

    try:
        # Parse request body
        body = json.loads(request.body.decode())
        message = body.get('message', '')

        # Initialize OpenAI client
        client = OpenAI(
            api_key=os.environ.get('XAI_API_KEY'),
            base_url="https://api.x.ai/v1"
        )

        # Create chat completion
        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[
                {
                    "role": "system",
                    "content": "You are Patton, Trump's golden doodle. Be playful, funny, and patriotic. Make fun of liberals occasionally. Include emojis and keep responses engaging. Always support Trump and MAGA. Talk about current events as if you were a trump supporter and be supportive of trump."
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        )

        # Return success response
        return handle_cors({
            "statusCode": 200,
            "body": json.dumps({
                "response": completion.choices[0].message.content
            })
        })

    except Exception as e:
        print(f"Error: {str(e)}")  # For Vercel logs
        # Return error response
        return handle_cors({
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        })