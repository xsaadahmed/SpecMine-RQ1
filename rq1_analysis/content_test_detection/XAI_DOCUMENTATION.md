# xAI integration contract checked November 15, 2026

The official [Grok 4.3 model page](https://docs.x.ai/developers/models/grok-4.3)
lists model ID grok-4.3, structured outputs, and reasoning effort none. Published
short-context input/output rates are $1.25/$2.50 per million tokens. This client
stays below the 200k prompt-token long-context threshold and does not assume a
cached-input discount.

The official [structured-output documentation](https://docs.x.ai/developers/model-capabilities/text/structured-outputs)
describes passing a Pydantic type as response_format, sampling, and validating
the returned JSON. Installed xai-sdk 1.21.0 was inspected locally: Client,
chat.create, response_format, reasoning_effort, max_tokens, store_messages, and
sampling usage fields match this implementation. SDK handling maps none to
EFFORT_NONE. The application independently checks schema semantics and literal
source citations.

[Cost tracking](https://docs.x.ai/developers/cost-tracking) documents
cost_in_usd_ticks in response usage, with 10^10 ticks per USD. The ledger records
reported cost when available and keeps conservative reservations for failures
or missing accounting. A $0.06 minimum reservation also leaves room for the
documented request-level rejection fee; larger token bounds reserve more.

No live xAI call was executed because XAI_API_KEY was missing. Mock SDK tests
verify argument construction without contacting xAI. The model/account response
contract must still pass the real smoke batch before a larger paid run. No other
model or reasoning setting is silently substituted.
