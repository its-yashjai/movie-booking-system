# 🚀 Movie Booking System - Simple Deployment Guide

Easy step-by-step guide to deploy your Movie Booking System to **Render** and **Vercel**.

---

## 🎯 Choose Your Platform

### Option 1️⃣: Deploy to Render Only (EASIEST ✨)
- Simplest setup
- Only needs 1 link
- Takes 2-3 minutes

### Option 2️⃣: Deploy to Vercel Only
- Requires more setup
- Needs 3 different credentials
- Takes 3-5 minutes

### Option 3️⃣: Deploy to Both (RECOMMENDED)
- Full redundancy
- Best for production
- Takes 5-8 minutes total

---

## 📋 RENDER DEPLOYMENT (EASIEST)

### ✅ Step 1: Create Render Service
1. Go to https://render.com (sign up if needed)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository
4. Choose a name (e.g., `movie-booking-app`)
5. Keep all settings default
6. Click **Create Web Service**
7. Wait for it to build (2-3 minutes)

### ✅ Step 2: Get Deploy Hook
1. In your Render service, go to **Settings**
2. Scroll down to **Deploy Hook** section
3. Click **Copy** button next to the webhook URL
4. Paste it somewhere safe (you'll need it)

**It looks like this:**
```
https://api.render.com/deploy/srv-xxxxx?key=xxxxx
```

### ✅ Step 3: Deploy with One Command
```bash
# Open terminal in your project folder
# Set the hook (paste your actual hook):
export RENDER_DEPLOY_HOOK='paste-your-hook-here'

# Deploy!
./deploy.sh render
```

**Done! ✅** Your app is now live on Render!

---

## � VERCEL DEPLOYMENT

### ✅ Step 1: Create Vercel Project
1. Go to https://vercel.com (sign up if needed)
2. Click **Import Project**
3. Select your GitHub repository
4. Click **Deploy**
5. Wait for deployment to complete

### ✅ Step 2: Get Your Tokens (Follow Exactly!)

**A. Token:**
1. Go to https://vercel.com/account/tokens
2. Click **Create** button
3. Name it: `deployment`
4. Select: **Full Account**
5. Click **Create**
6. **Copy the token immediately** (save it!)

**B. Organization ID:**
1. Go to https://vercel.com/account/settings
2. Look for **ID** on the page
3. Copy and save it

**C. Project ID:**
1. Go to your project settings in Vercel
2. Look for **Project ID** section
3. Copy and save it

### ✅ Step 3: Deploy with Command
```bash
# In your project terminal:
export VERCEL_TOKEN='your-token-here'
export VERCEL_ORG_ID='your-org-id-here'
export VERCEL_PROJECT_ID='your-project-id-here'

# Deploy!
./deploy.sh vercel
```

**Done! ✅** Your app is live on Vercel!

---

## 📋 DEPLOY TO BOTH (RECOMMENDED)

**If you have both Render and Vercel set up:**

```bash
# Set all variables
export RENDER_DEPLOY_HOOK='your-render-hook'
export VERCEL_TOKEN='your-vercel-token'
export VERCEL_ORG_ID='your-org-id'
export VERCEL_PROJECT_ID='your-project-id'

# Deploy to both at once!
./deploy.sh all
```

**That's it!** 🎉

---

## 🔄 Update Your App Later

Whenever you make changes and want to deploy:

```bash
# 1. Save your changes
git add .
git commit -m "Your changes description"

# 2. Deploy (example: Render only)
./deploy.sh render

# Or deploy to both
./deploy.sh all
```

---

## 🆘 Common Issues & Fixes

### "I keep forgetting my tokens!"

**Solution:** Create a file called `.env.deployment`:

```bash
# Create file
nano .env.deployment

# Add this (with your real values):
RENDER_DEPLOY_HOOK=your-hook-here
VERCEL_TOKEN=your-token-here
VERCEL_ORG_ID=your-org-id-here
VERCEL_PROJECT_ID=your-project-id-here

# Then every time you deploy, just do:
source .env.deployment
./deploy.sh all
```

**Important:** Add `.env.deployment` to `.gitignore` so tokens don't get uploaded!

### "Deploy says 'uncommitted changes'"

**Fix:**
```bash
git add .
git commit -m "Ready to deploy"
./deploy.sh render
```

### "I lost my Vercel token!"

**Don't worry! Generate a new one:**
1. Go to https://vercel.com/account/tokens
2. Click **Create** again
3. Copy the new token
4. Update your environment variable

### "Deployment fails?"

1. Check if you're on the `main` branch: `git branch`
2. Make sure all changes are committed: `git status`
3. Verify your tokens/hooks are correct
4. Try again: `./deploy.sh all`

---

## ✅ Deployment Checklist

Before you deploy:

- [ ] All code changes saved and committed
- [ ] You're on the `main` branch
- [ ] You have your Render hook OR Vercel tokens
- [ ] Your database migrations are applied
- [ ] Your `.env` file is properly configured

---

## 📞 Need Help?

**Render:** https://docs.render.com/deploy-hooks

**Vercel:** https://vercel.com/docs

**This Repo:** Check the `deploy.sh` script for more details

---

**Version:** 2.0 - Simplified  
**Updated:** March 8, 2026  
**For:** Beginners and busy developers
