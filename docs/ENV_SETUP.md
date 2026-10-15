# `.env` setup: how to get every value

1. Open `.env` in the project root. It already exists, and it's git-ignored, so it never gets committed.
2. Fill in the values below.
3. Restart the app.

**Only `GEMINI_API_KEY` is needed to turn the agent on. Everything else already works locally.**

| Variable | Needed? | Where it comes from |
|---|---|---|
| `GEMINI_API_KEY` | **Yes**, for the agent | Google AI Studio (step 1) |
| `GEMINI_MODEL` | Optional | Default `gemini-3.5-flash` (step 1) |
| `LLM_PROVIDER` | Already set | `gemini`. Leave it. |
| `FALKORDB_HOST`, `FALKORDB_PORT` | Already set for local use | Docker locally (step 2), or FalkorDB Cloud for the live demo (step 3) |
| `FALKORDB_USERNAME`, `FALKORDB_PASSWORD` | Only for FalkorDB Cloud | FalkorDB Cloud (step 3) |
| `CHOKEPOINT_SECRET` | Already generated | Random string. Keep it secret. |
| `CHOKEPOINT_ADMIN_TOKEN` | Already generated | Opens `/admin?token=…` |
| `ANTHROPIC_API_KEY` | No | Only if you switch to `LLM_PROVIDER=anthropic` |

## 1. Gemini API key (free tier available)

1. Go to **https://aistudio.google.com/apikey** and sign in with a Google account.
2. Click **Create API key**, pick or create a Google Cloud project, and copy the key. It starts with `AIza…`.
3. Paste it into `.env`:

   ```
   GEMINI_API_KEY=AIza...your-key...
   ```

4. **Model:** `gemini-3.5-flash` is the default.
   - To use a newer or stronger model, check the model list at https://ai.google.dev/gemini-api/docs/models and set, for example, `GEMINI_MODEL=gemini-3.8-flash`.
   - Use a model that supports **function calling**.
5. **Check it works:**

   ```bash
   python -m chokepoint.cli ask F-1           # should end with status "chosen", plan G-101 + G-106
   python -m chokepoint.cli eval -n 3         # the gate before recording the video: needs 3/3 PASS
   ```

   **Free-tier limit:** Google allows only **20 requests per model per day** on a free key, and one triage uses about 6. That's about 3 agent runs a day.
   - When the quota runs out, the app still works: it shows the graph's cheapest plan, labelled "daily Gemini quota used up".
   - **For the live demo and judging, turn on billing:** AI Studio → **Get API key → your project → Set up billing**. Flash models cost a fraction of a cent per triage, and the app caps spend at 300 runs a day.
   - Per-minute limits (429) and "model busy" (503) are retried automatically.

   If `eval` fails for a reason other than quota, try a newer model (`gemini-3.8-flash`, or `gemini-3.1-pro-preview` with billing on) and run it again.
6. **Optional:** have Gemini extract the knowledge links (Track 03) instead of using the hand-written fallback:

   ```bash
   python -m chokepoint.cli ingest
   python -m chokepoint.cli seed
   ```

   Seeding fails loudly if the extraction misses an edge the demo needs.

## 2. FalkorDB locally (no account needed)

```bash
docker run -d --name falkordb -p 6379:6379 -p 3000:3000 falkordb/falkordb:latest
```

- `.env` already has `FALKORDB_HOST=localhost` and `FALKORDB_PORT=6379`.
- Leave the username and password empty.
- Open http://localhost:3000 for the FalkorDB Browser, where you can look at the graph.
- Or run everything at once: `docker compose up --build`. Compose reads `GEMINI_API_KEY` from `.env`.

## 3. FalkorDB Cloud (for the live deployment)

1. Go to **https://app.falkordb.cloud/** and sign up. The free tier is enough.
2. **Create a database** (any region close to you), then open it and find **Connection details**.
3. Copy the values into `.env` on the server, or into your host's environment variables:

   ```
   FALKORDB_HOST=r-xxxx.falkordb.cloud     # the host shown
   FALKORDB_PORT=12345                     # the port shown
   FALKORDB_USERNAME=falkordb              # the username shown
   FALKORDB_PASSWORD=...                   # the password shown
   ```

4. **Check it works:** `python -m chokepoint.cli seed` should print `"template": "tmpl_…"`. Then run `pytest`: it reads `.env`, so it runs against the cloud.

**Verified on 2026-10-02** with the free tier on AWS `ap-south-1`. The seed, all tests, per-visitor copies and the web app work.
- The cloud user may only run `GRAPH.*` commands; plain Redis commands such as `GET` and `ZADD` are denied.
- The app therefore keeps its bookkeeping (template pointer, visitors, rate limits) in a small `chokepoint_meta` graph.
- Use `CHOKEPOINT_MAX_GRAPHS=20` on the free tier.

## 4. Hosting the app (live URL)

Render, Railway and Fly all build the `Dockerfile` directly. Render as the example:

1. Push the repo to GitHub. **Do this on Oct 15.**
2. On https://render.com: **New → Web Service → connect the repo**, then choose **Docker**.
3. Add the environment variables from your `.env` (Gemini key, FalkorDB Cloud values, secret, admin token).
4. Deploy, then open `https://<your-app>.onrender.com/healthz`. It should show:

   ```json
   {"falkordb": true, "template": "tmpl_…", "llm": true, "provider": "gemini"}
   ```

## Safety

- **Never commit `.env`.** It's in `.gitignore`. Only `.env.example`, which has no secrets, gets committed.
- **If a key leaks:** delete it in AI Studio and create a new one.
- **Spend:** the demo caps LLM runs at 10 per visitor per hour and 300 per day. You can change this with `CHOKEPOINT_RUNS_PER_HOUR` and `CHOKEPOINT_RUNS_PER_DAY`.
