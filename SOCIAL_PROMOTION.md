# 📣 Social Promotion Templates

Use these snappy, high-impact posts to share the project on social media.

---

## 🏎️ Reddit (r/Slack) - "The Scrolling Fix"
**Title:** I built a tool to automate Slack emoji uploads and fix "Tiny" icons.

**Body:**
Manual emoji uploads are a nightmare. I built a cross-platform tool to automate the whole process.

*   **🤖 Bulk Uploads:** Playwright robot with API verification (no "ghost" uploads).
*   **🔲 Auto-Squaring:** Fixes the "tiny thin strip" bug.
*   **🎨 Smart Transparency:** Flood-fill that protects logo centers.
*   **🗜️ GIF Squeezer:** Tries to beat the "too big" error.

**Honest Note:** Automates ~95% of the library. Extremely complex GIFs still hit Slack's size gate.

**Repo:** https://github.com/CynthiaWahome/slack-emoji-pipeline
**Gist:** https://gist.github.com/CynthiaWahome/7cef9951dd0cb7ed3caaf0e63d7774a7

---

## 🦋 Bluesky - "The Quick Pitch"
Finally fixed my Slack emoji workflow! 🤖🚀

Built a cross-platform pipeline to automate bulk uploads and fix those annoying "tiny icon" and "invisible logo" bugs.

Features:
✅ Playwright automation
✅ Smart flood-fill
✅ GIF frame decimation

Check it out: https://github.com/CynthiaWahome/slack-emoji-pipeline

#slack #automation #python #playwright #opensource



  Title: I built a tool to automate the bulk uploading of
  Slack custom emojis.

  Body:
  > If you’ve ever had to manually upload hundreds of custom
  emojis to Slack, you know how tedious it is. I built a
  cross-platform tool to automate the entire process from
  your computer.
  > 
  > The Core Win:
  > It uses a Playwright robot to handle the bulk work. It
  identifies your files, skips duplicates via an API Guard,
  and verifies every upload so you don't get "ghost" results.
  > 
  > Added Quality-of-Life Fixes:
  > I also integrated automated logic to help with common
  rendering issues:
  >    🔲 Squaring:* Pads wide icons so they don't look tiny
  in chat.
  >    🎨 Transparency:* A smart flood-fill that cleans
  backgrounds while protecting logo centers.
  >    🗜️ Decimation:* Drops frames in GIFs to *try* and beat
  Slack's complexity limits.
  > 
  > Real-World Honesty:
  > It’s not a 100% fix for everything yet. Extremely complex
  GIFs still hit Slack's "Image is too big" error even after
  resizing. It automated about 95% of my library, but the
  most difficult files still required a manual touch.
  > 
  > If you need to get a large collection into Slack without
  losing your mind to manual clicking, this is for you.
  > 
  > Repo:
  https://github.com/CynthiaWahome/slack-emoji-pipeline
  > 
  > Browser-Console Gist:
  https://gist.github.com/CynthiaWahome/7cef9951dd0cb7ed3caaf
  0e63d7774a7
  > 
  > Hopefully this helps some of you automate your next
  workspace migration!
  > 
  > #slack #emoji #automation #playwright #python


--
**Title: I automated bulk Slack emoji uploads with Playwright — open source, still rough around the edges**

My workspace had 200+ custom emojis to upload and clicking through Slack's UI one by one wasn't happening.

So I built a 3-stage Python pipeline:

- **Sanitiser** — resizes images, decimates oversized GIFs (Slack silently rejects anything >50 frames)
- **Rename wizard** — interactive CLI that opens each emoji for preview, applies your namespace tag, catches collisions
- **Uploader** — Playwright automation that checks the live emoji list via API before uploading, so no ghost duplicates

It got ~95% of my library into Slack without touching the UI. The remaining 5% (extremely complex GIFs, some transparency edge cases) still need manual work — I haven't fully solved that yet.

**Repo:** https://github.com/CynthiaWahome/slack-emoji-pipeline
**Console-only Gist** (just bulk upload, no Python needed): https://gist.github.com/CynthiaWahome/7cef9951dd0cb7ed3caaf0e63d7774a7

Currently Mac/Brave only. If anyone's tackled cross-platform Playwright browser auth for Slack or has ideas on the GIF compression wall, I'd genuinely love the input.

--
BLUESKY 
built a python pipeline to bulk-upload custom slack emojis 👀

slack has no public API for this (bots can’t add emojis), so it uses playwright to drive a real browser session + checks the live emoji list first to skip duplicates

handles 200 emojis without touching the ui. some edge cases (complex gifs, tricky transparency) still need manual help — wip

github.com/CynthiaWahome/slack-emoji-pipeline

#python #automation #opensource #slack

---

## 🏎️ Reddit: The "Rough around the edges" Final
**Title:** I automated bulk Slack emoji uploads with Playwright — open source, still rough around the edges.

**Body:**
Manual emoji uploads are a nightmare. I got tired of Slack's "too big" errors and tiny icons, so I built a 3-stage Python pipeline:

1. **Sanitizer:** Resizes images and decimates oversized GIFs.
2. **Rename Wizard:** Interactive CLI for identification and namespacing.
3. **Uploader:** Playwright automation with API Guard (no ghost duplicates).

It got ~95% of my library into Slack without me touching the UI. The remaining 5% still need manual work—I haven't fully solved that yet.

**Repo:** https://github.com/CynthiaWahome/slack-emoji-pipeline
**Toolkit Gist (Bulk upload & surgical mass delete):** https://gist.github.com/CynthiaWahome/7cef9951dd0cb7ed3caaf0e63d7774a7

---

## 🏎️ Reddit: The "No Public API" Refined
**Title:** I automated Slack custom emoji uploads with Playwright (because there’s no public API).

**Body:**
Since Slack has no public API for custom emojis in standard workspaces, I built a Python-based Playwright pipeline to automate the entire process.

It handles the heavy lifting while bypassing Slack's hidden complexity and frame-rate limits.

**The 3-Stage Engine:**
* **🗜️ Sanitizer:** Automatically resizes images and decimates oversized GIFs (to beat the 50-frame limit).
* **🧙‍♂️ Rename Wizard:** Interactive CLI for visual identification and bulk namespacing.
* **🤖 Uploader:** Playwright automation with an API Guard to skip duplicates and verify every upload.

**Full Transparency:**
It got ~95% of my library into Slack without me touching the UI. The remaining 5% (extremely complex GIFs with 100+ frames) still hit Slack’s internal compression wall and required manual touch-ups.

**Repo:** https://github.com/CynthiaWahome/slack-emoji-pipeline
**Toolkit Gist:** https://gist.github.com/CynthiaWahome/7cef9951dd0cb7ed3caaf0e63d7774a7

If anyone has ideas on beating Slack's final GIF compression gate or optimizing cross-platform sessions, I’d love to hear them! 🚀
