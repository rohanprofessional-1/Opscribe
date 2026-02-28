# Nginx setup for anonymous client UUID

This folder configures nginx so each visitor gets a **unique UUID** used to scope their data. The UUID is created by the API; nginx’s job is to pass it securely to the backend.

## Flow

1. **First visit**  
   Browser has no cookie. Frontend calls `GET /api/clients/anon/session`.  
   Backend creates a new `Client` (name `"Anonymous"`, id = new UUID), returns it and sets cookie:
   `Set-Cookie: anonymous_client_id=<uuid>; HttpOnly; Path=/; Max-Age=...; SameSite=Lax`.

2. **Later requests**  
   Browser sends `Cookie: anonymous_client_id=<uuid>` on every request to your domain.  
   Nginx, when proxying to the API, sets `X-Client-ID: $cookie_anonymous_client_id` so the backend always receives the client id.

3. **Security**  
   - Cookie is **HttpOnly** (not readable by JS).  
   - Backend can trust `X-Client-ID` when nginx is the only entry point (e.g. internal proxy).  
   - All client-scoped endpoints (graphs, nodes, edges) use this id so each anonymous visitor only sees their own data.

## Using this config

1. **Install nginx** (e.g. `brew install nginx` on macOS).

2. **Mount the snippet**  
   Either include `opscribe.conf` inside a `server {}` (and remove the duplicate `server` from the file), or run nginx with this as the main config:
   ```bash
   nginx -c /path/to/Opscribe/nginx/opscribe.conf
   ```
   Adjust `upstream` ports if your frontend and API run on different ports (e.g. Vite on 5173, API on 8000).

3. **Base URL for API**  
   With the config as-is, the API is exposed under `/api/` (e.g. `https://yourdomain.com/api/clients/anon/session`). Point your frontend API client at `baseURL = '/api'` (or `https://yourdomain.com/api`) when behind this nginx.

4. **First request**  
   Frontend should call `GET /api/clients/anon/session` once on load (or before any other API call). The response sets the cookie; nginx will send `X-Client-ID` on all subsequent `/api/` requests.

## Optional: generate UUID in nginx (njs)

If you want the **UUID to be generated at the edge** (nginx) instead of by the API, you need the **njs** module and a small script that:

- Runs on the first request (no `anonymous_client_id` cookie).
- Generates a UUID (e.g. with njs `crypto` or a small UUID routine).
- Sets a response header `Set-Cookie: anonymous_client_id=<uuid>; ...` and then proxies to the backend.

That requires building nginx with njs or using OpenResty. The approach above (API creates UUID and sets cookie, nginx only forwards it) works with a plain nginx install and is the recommended setup.
