from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI
import sys

def handler(request):
    print("Handler started")  # Debug log

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type": "application/json"
    }

    # Handle preflight request
    if request.method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }

    try:
        # Check for API key
        api_key = os.environ.get('XAI_API_KEY')
        if not api_key:
            raise ValueError("XAI_API_KEY not found in environment variables")

        # Parse request body
        try:
            body = json.loads(request.body.decode())
            message = body.get('message')
            if not message:
                raise ValueError("No message provided in request")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in request body: {str(e)}")

        # Initialize OpenAI client
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )

        # Create chat completion
        try:
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
            response = completion.choices[0].message.content
        except Exception as e:
            raise ValueError(f"Error calling xAI API: {str(e)}")

        # Return success response
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "response": response
            })
        }

    except Exception as e:
        print(f"Error in handler: {str(e)}")  # This will show in Vercel logs
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": f"Server error: {str(e)}"
            })
        }