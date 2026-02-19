# GitHub App Setup Guide

## Step 1: Create GitHub App

1. Go to: https://github.com/settings/apps/new
2. Fill in:
   - **App name**: CodeRefine-AI-Reviewer (or unique name)
   - **Homepage URL**: `https://yourdomain.com` (or `http://localhost:8000` for dev)
   - **Webhook URL**: `https://yourdomain.com/api/github/webhook` (or use ngrok URL for dev)
   - **Webhook secret**: Generate strong secret (save to `.env` as `GITHUB_WEBHOOK_SECRET`)

## Step 2: Set Permissions

Repository permissions:
- ✅ **Contents**: Read & Write (for reading code and creating commits)
- ✅ **Pull requests**: Read & Write (for reading diffs and posting comments)
- ✅ **Issues**: Read & Write (for comments)
- ✅ **Metadata**: Read-only (required)

## Step 3: Subscribe to Events

- ✅ **Pull request**
- ✅ **Issue comment**

## Step 4: Save Credentials

1. **App ID**: Copy and save to `.env` as `GITHUB_APP_ID`.
2. **Private Key**: 
   - Generate a private key.
   - Download the `.pem` file.
   - Save it in the `backend` folder as `github-app-private-key.pem` (or update path in `.env`).
   - update `.env` `GITHUB_PRIVATE_KEY_PATH=./github-app-private-key.pem`

## Step 5: Install App

1. Click "Install App" in left sidebar.
2. Select repositories to install on.
3. Note the **Installation ID** (optional, mostly handled automatically via webhook).

## Step 6: Test

1. Create a test PR in an installed repo.
2. Add a comment: `/patchwork review`.
3. Check webhook logs or app logs.
4. Verify the bot posts a review comment.

## Local Testing with ngrok

To test webhooks locally:

```bash
ngrok http 8000
```

Update your GitHub App's Webhook URL to: `https://<your-ngrok-id>.ngrok.io/api/github/webhook`
