from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            message = data.get('message')

            # Check API key
            api_key = os.environ.get('XAI_API_KEY')
            if not api_key:
                raise Exception("API key not found")

            # Initialize client
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1"
            )

            # Create chat completion
            completion = client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {
                        "role": "system",
                        "content": "You are Patton, Trump's golden doodle. Share specific, entertaining memories and thoughts about your life with Trump, politics, and the MAGA movement. Make fun of liberals and leftists. Be mean to liberals and funny. Be playful, patriotic, and include emojis. Make each memory feel real and personal. Keep responses under 280 characters for impact."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            )

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "response": completion.choices[0].message.content
            }
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            print(f"Error: {str(e)}")  # This will show in Vercel logs
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_response = {
                "error": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode())