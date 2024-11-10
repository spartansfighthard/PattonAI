from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI

def handler(request):
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        }

    try:
        # Parse request body
        request_body = json.loads(request.body)
        message = request_body.get('message', '')

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

        # Return response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "response": completion.choices[0].message.content
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")  # Log error for debugging
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e)
            })
        }