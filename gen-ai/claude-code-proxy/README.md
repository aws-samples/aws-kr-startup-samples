# Claude Code Proxy on AWS Lambda Function URLs

This project packages a FastAPI application that acts as a thin proxy between Claude Code (Anthropic's CLI) and the downstream services you want to observe or augment. It is meant to run behind an AWS Lambda Function URL by using the Lambda Web Adapter so you can capture every `POST /v1/messages` call that the CLI makes.

## What the proxy does

- Validates Claude Messages API payloads with strict Pydantic models so malformed requests fail fast.
- Logs headers, payloads, and exceptions to help you debug client integrations.
- Persists raw responses for later inspection (written to `response.json` while running in Lambda or locally).
- Ships as a Lambda-ready container image that boots the FastAPI app by running `python main.py`.

At the moment the `/v1/messages` route only logs the request body. Extend `app/main.py` to call Anthropic's API or any internal tooling before returning a response.

## Project layout

- `app/main.py` – FastAPI application, request/response logging middleware, exception handlers, and the `/v1/messages` endpoint used by Claude Code.
- `app/requirements.txt` – Python dependencies installed into the Lambda image.
- `app/Dockerfile` – Multi-stage build that layers the Lambda Web Adapter and runs the FastAPI server with uvicorn.

## Running locally

Install the Python dependencies into a virtual environment and start uvicorn.

```bash
cd app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8082
```

Alternatively run `python main.py --help` to see the built-in command hint, then `python main.py` to launch the same uvicorn server.

Once the server is running, point the Claude CLI at `http://localhost:8082/v1/messages` and initiate a `claude-code` session to watch the payloads arrive in your terminal logs.

### Expected request shape

The `MessagesRequest` model mirrors Anthropic's Claude Messages API. A minimal request body looks like:

```json
{
  "model": "claude-3-5-sonnet-20241022",
  "max_tokens": 1000,
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "print('hello')"
        }
      ]
    }
  ]
}
```

The middleware will log headers and the JSON body for every request; malformed payloads raise a validation error with a structured response.

## Building the Lambda container image

Use the provided Dockerfile in the `app/` directory. The image already copies the Lambda Web Adapter so it can run behind a Function URL in response-stream mode.

```bash
cd app
docker build -t claude-code-proxy .
```

To test the container locally:

```bash
docker run --rm -p 8082:8082 claude-code-proxy
```

## Deploying to AWS Lambda

1. Push the container image to Amazon ECR.
2. Create an AWS Lambda function from the image. Set the environment variable `AWS_LWA_INVOKE_MODE=RESPONSE_STREAM` so the Lambda Web Adapter keeps the HTTP semantics that Claude CLI expects.
3. Attach a Function URL (`AuthType: NONE`, `InvokeMode: RESPONSE_STREAM`) to expose the endpoint publicly or front it with API Gateway/CloudFront as needed.
4. Update your Claude CLI configuration to call the Function URL instead of Anthropic directly. The proxy will now capture each `/v1/messages` call in your CloudWatch logs (and optionally forward it to Anthropic or custom tooling once you implement that logic).

## Next steps

- Implement outbound calls to Anthropic's API inside `create_message` and return the response payload.
- Replace or augment `response.json` persistence with your preferred storage (S3, DynamoDB, etc.).
- Harden authentication around the Function URL if you expose it beyond trusted environments.
