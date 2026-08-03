# Command Desk — Dispatch Checklist

The plan, start to finish. Two jobs running together: strip the front back to just Nova, and wire the first real worker (mail) end to end. Tick as you go.

Rule that doesn't change: **the live Python backend at airexploit.com/commanddesk stays untouched.** Back it up before any deploy. Frontend files get replaced; Python does not get overwritten or restarted.

---

## PART ONE — THE FACE (the restart)

Goal: open the app and it's just Nova. No tiles, no icon row. You talk, she routes. Workers still exist, they live behind her.

- [ ] **1.1 — Strip the front screen to just Nova.** Remove the tile grid / icon row from the home view. Home becomes: Nova (the video background build) + a way to talk to her. Nothing else on screen.
- [ ] **1.2 — Keep the live voice.** The real-time listen-and-reply you've already got in progress stays. This is what makes "just talk to her" work instead of a text box.
- [ ] **1.3 — She routes.** Hub already does this. Point it at the conversation instead of buttons: "anything come in?" → mail worker; "I've got coding to do" → coding worker. Routing happens behind her, invisible.
- [ ] **1.4 — Deploy the stripped front.** Back up /var/www/commanddesk first. Deploy frontend + assets (**including assets/video/**). Leave Python alone. Curl for HTTP 200.

---

## PART TWO — THE HANDS (mail worker, first real job)

Goal: one worker reads a real email and surfaces it in the app. Reading only at first. No sending until it's proven.

- [ ] **2.1 — Check what Google integration already exists.** Before building anything: is there a Google OAuth app / client credential for Gmail already on the box? Any account authorised? Report what's there and what's missing. Don't build yet.
- [ ] **2.2 — Create the Google OAuth app.** *(Sam only — the gate only you can open.)* On Google's side, create the OAuth app and switch on Gmail scope (and Calendar if you want it later). This is Google handing the box a key.
- [ ] **2.3 — Install the key on the box.** *(Dispatch.)* Client ID + secret into .env at 600 perms, same handling as the Anthropic key. Never pasted in plain chat.
- [ ] **2.4 — Do the one-time "allow" handshake.** Authorise your Gmail account against the OAuth app so the box holds the mailbox key. This is the second key — brain key (API) + mailbox key (OAuth).
- [ ] **2.5 — Teach the mail worker.** Its prompt: check for new mail, read it, decide what matters, draft a reply. Brain + instructions.
- [ ] **2.6 — Safe first test: READ ONLY.** Worker reads one real email and reports back. No drafting sent, no sending. Proves the connection with zero risk of anything going out in your name.
- [ ] **2.7 — Surface it in the app.** Result shows up in Nova's voice: "here's what came in." Plain and ugly is fine at this stage — the point is proving it's real.
- [ ] **2.8 — Turn on drafting.** Worker drafts a reply, shows you the words, waits. Still nothing sent.
- [ ] **2.9 — Turn on sending, behind your yep.** Once reading + drafting are trusted, allow sending — held behind your approval each time until you trust it. Can be set per worker.

---

## PART THREE — CLONE IT

Goal: once one worker works end to end, the rest are copies.

- [ ] **3.1 — Clone the pattern.** Coding, calendar, whatever's next. Don't build six from scratch — copy the proven mail pattern and swap the app + prompt.

---

## WHO DOES WHAT

- **Sam only:** 2.2 (create Google OAuth app), 2.4 (approve the "allow").
- **Dispatch on the box:** everything else — the deploys, the key install, the worker wiring.
- **Claude (me):** writes the worker prompts and wiring specs you hand to Dispatch. I can't reach the box or Gmail from here.

## DECISIONS STILL OPEN (not needed to start)

- [ ] Does mail send on its own, or draft-and-wait-for-yep? *(Recommend draft-and-wait for the first while.)*
- [ ] Which model drives the mail worker — paid Claude for quality, or Ollama to keep it free?
