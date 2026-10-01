# Hosted free-tier campus assistant

Provider: Groq. Default model: openai/gpt-oss-20b. Check your account Free Plan limits at https://console.groq.com/settings/limits. Do not enable a paid plan if you want free-tier-only usage. No paid provider fallback is configured. AWS hosting still consumes Learner Lab credits.

1. Create a Groq account and API key at https://console.groq.com/keys. Keep the key private; never paste it into frontend code or commit it.
2. Set GROQ_API_KEY in the backend process environment (AWS Lambda environment configuration, or the service environment on your server). Optional GROQ_MODEL overrides the model.
3. Restart the backend. The existing frontend calls POST /api/chat; configure your AWS API routing to forward POST /chat to this backend. A request takes up to 20 seconds at the provider; allow a compatible gateway timeout.
4. Ask a room question. Each request sends the question and an allowlisted room snapshot for the selected timestamp to Groq. No user table is sent. Chat is single-turn: follow-ups should repeat relevant constraints.

No key means an explicit 503 setup message, not a fake AI answer. Provider failures and quota exhaustion are reported to the user. Room links are checked against database IDs; generated prose still needs normal user verification. Booking actions are not supported.

Demo guard: five requests per minute per backend process; message length 800 characters and output limit 1200 tokens. This limiter is not shared across AWS instances. Before public deployment, require your project's authentication and configure shared gateway throttling/quota controls. The frontend proxy limits POST bodies to 8 KB; configure the cloud gateway similarly. Keep keys out of logs and source control. No chat messages are persisted by this application.

Run tests: python -m unittest src.backend.test_chat. Tests use a mocked provider and make no paid/network requests. Live provider verification requires your own key and outbound HTTPS access. Source: https://console.groq.com/docs/rate-limits

Local development can also read GROQ_API_KEY from the ignored repository-root .chat.local.json object. Never deploy or commit that file; AWS should use the backend environment variable.
