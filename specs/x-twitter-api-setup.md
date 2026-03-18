# X/Twitter API Setup Guide for Sharp Picks

## What You Need

You're posting 5-7 tweets per week manually. You don't need the API for that - just use the app or a free scheduler like Buffer or Typefully. But if you want to eventually automate results recaps or process tweets from your Railway backend, here's the full setup.

## Do You Actually Need the API?

For your current situation, probably not yet. Here's the decision:

**Just use a scheduling tool if:**
- You want to batch-write tweets from the tweet bank and schedule them for the week
- You're posting manually and just want a queue
- You don't want to write any code for this right now

**Best free/cheap options:**
- **Typefully** - free tier, built for writers, drafts + scheduling, analytics. Good fit for Evan's voice since it's thread-friendly.
- **Buffer** - free tier handles 3 channels, 10 scheduled posts per channel. Enough for your cadence.
- **TweetDeck/X Pro** - built into X, free with premium, lets you schedule natively.

**Set up the API if:**
- You want your Railway backend to auto-post results recaps after games settle (e.g., "Last night: 2-1. Season: 47-38. CLV +1.2%.")
- You want the market notes cron to trigger a tweet when a new journal entry publishes
- You want to build toward full automation later

If you want the API, here's the walkthrough.

---

## Step 1: Create a Developer Account

1. Go to **https://developer.x.com/en/portal/petition/essential/basic-info**
2. Sign in with the Sharp Picks X account (or Evan Cole's account, whichever you're posting from)
3. Select **"Sign up Free Account"** at the bottom - this gives you 1,500 posts/month which is more than enough for 5-7/week
4. Fill out the use case description. Something like: "Automated posting of sports analytics results and content promotion for a sports betting analytics platform."
5. Agree to the developer agreement
6. You'll land in the Developer Portal immediately

---

## Step 2: Create a Project and App

1. In the Developer Portal, click **"Projects & Apps"** in the left sidebar
2. Click **"+ Add Project"**
3. Name it: `sharp-picks-social`
4. Use case: select "Making a bot" or "Managing content"
5. Describe it: "Posts automated results recaps and content teasers for Sharp Picks, a sports analytics platform."
6. Click **Next** to create an App within the project
7. Name the app: `sharp-picks-poster`
8. You'll see your **API Key** and **API Secret Key** - copy these immediately and store them. You won't see the secret again.

---

## Step 3: Set Up Authentication

For posting tweets, you need **OAuth 1.0a** (User Authentication) - not just a Bearer Token, which is read-only.

1. In your app settings, go to **"User authentication settings"** and click **Set up**
2. App permissions: select **"Read and write"**
3. Type of App: select **"Web App, Automated App or Bot"**
4. Callback URL: `https://app.sharppicks.ai/callback` (or any URL you control - you won't actually use this for server-to-server posting, but it's required)
5. Website URL: `https://sharppicks.ai`
6. Click **Save**

Now go to the **"Keys and Tokens"** tab:
1. Under **"Authentication Tokens"**, generate your **Access Token and Secret**
2. Make sure these are generated with **Read and Write** permissions
3. Copy all four values:
   - API Key (Consumer Key)
   - API Secret Key (Consumer Secret)
   - Access Token
   - Access Token Secret

---

## Step 4: Store Credentials in Railway

In your Railway project, add these environment variables:

```
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
```

Never hardcode these in your codebase.

---

## Step 5: Install the Python Library

Add `tweepy` to your requirements.txt:

```
tweepy>=4.14.0
```

---

## Step 6: Basic Posting Code

```python
import tweepy
import os

def post_tweet(text):
    """Post a tweet using X API v2 via OAuth 1.0a."""
    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )

    response = client.create_tweet(text=text)
    return response.data["id"]
```

That's it. `tweepy` handles the OAuth signing for you.

---

## Step 7: Optional - Automate Results Recaps

If you want your grading cron to auto-post results, add a function that runs after picks are graded:

```python
def compose_results_tweet(nightly_record, season_record, clv):
    """Compose a results recap tweet from grading data."""
    w, l = nightly_record
    sw, sl = season_record

    if w + l == 0:
        return None  # No picks to report

    clv_str = f"+{clv:.1f}" if clv > 0 else f"{clv:.1f}"

    tweet = (
        f"Last night: {w}-{l}. "
        f"Season: {sw}-{sl}. "
        f"CLV: {clv_str}%. "
        f"Process is process - every night gets posted."
    )

    return tweet


# In your grading cron, after picks are graded:
tweet_text = compose_results_tweet(
    nightly_record=(2, 1),
    season_record=(47, 38),
    clv=1.2
)

if tweet_text:
    post_tweet(tweet_text)
```

**Important:** Add a flag/env var like `X_AUTO_POST=true` so you can disable this without redeploying. You probably want to run this manually for a few weeks before going fully auto.

---

## Step 8: Optional - Tweet When Journal Publishes

When a new journal entry is created, post the teaser:

```python
def compose_journal_tweet(article_title, article_url, teaser_line):
    """Compose a journal article teaser tweet."""
    tweet = f"{teaser_line}\n\n{article_url}"

    # X character limit is 280
    if len(tweet) > 280:
        # Trim teaser, keep URL
        max_teaser = 280 - len(article_url) - 5  # 5 for \n\n and buffer
        tweet = f"{teaser_line[:max_teaser]}...\n\n{article_url}"

    return tweet
```

---

## Rate Limits (Free Tier)

- **1,500 posts/month** - you'll use maybe 30-40. Not a concern.
- **50 requests per 15-minute window** for posting. Not a concern.
- **No read access** on Free tier - you can't pull mentions, search tweets, or read timelines via the API. You'd need Basic ($100/mo) for that. Not needed for your use case.

---

## Recommendation

Start with **Typefully or Buffer** for the next 4-6 weeks. Batch-load the tweet bank, schedule the article teasers to match the publishing calendar, and post results recaps manually each morning.

Once you're comfortable with the cadence and voice, add the API integration for auto-posting results recaps only. Keep everything else manual - the philosophy and hot take tweets land better when they feel spontaneous, not scheduled.

The API setup takes about 15 minutes. The code is maybe 20 lines. The hard part isn't the technical integration - it's deciding what to automate and what to keep human.
