# Deployment Guide: Aviation Operations Dashboard
**Status**: Recommendation Phase
**Target**: Public Access (Internet) from Local Infrastructure (Tunneling)

## ⚠️ Critical Constraint: AIMS Connectivity
Since this app relies on `aims_soap_client.py` connecting to an enterprise SOAP API (AIMS), moving the app to a public cloud (like Render/Heroku) usually **BREAKS** the connection because:
1.  AIMS often blocks unknown cloud IP addresses.
2.  AIMS might require a VPN connection that exists on your machine but not on the cloud.

## solution: Secure Tunneling (Cloudflare Tunnel)
Instead of moving the "Brain" (Server) to the cloud, we keep the Brain on your PC and create a secure "Wormhole" (Tunnel) to the internet.

### Advantages
*   ✅ **AIMS Access Guaranteed**: Uses your PC's existing network connection.
*   ✅ **Free**: Cloudflare Tunnel is free securely.
*   ✅ **Secure**: No need to open Router Ports.
*   ✅ **Fast**: Served via Cloudflare's global CDN.

---

## 🚀 Option 1: Instant Quick-Test (LOCALHOST.RUN)
*Best for showing someone right now.*

1.  Open Terminal.
2.  Run: `ssh -R 80:localhost:5001 nokey@localhost.run`
3.  Copy the URL printed (e.g., `https://someword.localhost.run`).
4.  Share it!
    *   *Note: URL changes every time you restart.*

---

## 🛡️ Option 2: Permanent Production (Cloudflare Tunnel)
*Best for long-term usage.*

### Prerequisite
*   A custom domain (e.g., `vj-ops.com`) usually required for persistent setup, OR use Quick Tunnels (`trycloudflare.com`).

### Setup Steps (Quick Tunnel)
1.  Download `cloudflared` (Windows exe).
2.  Run command:
    ```powershell
    cloudflared tunnel --url http://localhost:5001
    ```
3.  Copy the `https://....trycloudflare.com` URL.
4.  This URL stays active as long as the command runs.

---

## ☁️ Option 3: Full Cloud (Render/Railway)
*Only if AIMS is publicly accessible.*

1.  **Create Repository**: Push code to GitHub.
2.  **Connect Render**: Link GitHub repo.
3.  **Build Command**: `pip install -r requirements.txt`
4.  **Start Command**: `gunicorn api_server:app`
5.  **Environment**: Add secrets from `.env`.
6.  **WARNING**: Verify connection to AIMS immediately.

## Recommendation
Given "Type 2C" (No VPS), **Option 2 (Cloudflare Tunnel)** is the professional choice.
For right now, use **Option 1** to verify it works over the internet.
