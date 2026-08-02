# Dispatch — full run. Do all of it. Don't come back until it's done and tested.

This is one job, start to finish. Run it end to end. Make your own calls on anything left open (defaults are set below). **Do not ping Sam mid-run with questions.** Only report back when it is done, live, and you have tested it yourself.

**Hard rule:** the live Python backend at airexploit.com/commanddesk stays untouched. Back it up before any deploy. Replace frontend files; never overwrite or restart the Python. Straight quotes only in any command. Copy assets/video/* on deploy. Curl for HTTP 200 before you call any deploy done.

---

## STEP 1 — Strip the front to just Nova, deploy

- Back up /var/www/commanddesk first.
- Remove the tile grid / icon row from the home view. Home becomes: Nova (the talking-face build already live) + the way to talk to her. Nothing else on screen.
- Keep the live voice — the real-time listen-and-reply stays. That is what makes "just talk to her" work.
- Point the Hub router at the conversation, not buttons: "anything come in?" -> mail worker; "I've got coding to do" -> coding worker. Routing stays invisible, behind her.
- Deploy frontend + assets (including assets/video/). Leave Python alone. Curl HTTP 200.

## STEP 2 — Wire the mail worker, read-only, end to end

The Google OAuth app is already created and the credential JSON is downloaded (project command-desk-nova, Gmail API enabled). Sam is handing you that JSON.

- Check what Google integration already exists on the box first. Report nothing to Sam — just proceed.
- Install the credential: client ID + secret into .env at 600 perms, same handling as the Anthropic key. Never in plain chat.
- The one-time "allow" is the single thing that needs Sam's finger. Generate the consent URL, make it one tap, hand Sam that one link and nothing else. That is the only interruption allowed.
- Teach the mail worker its prompt: check for new mail, read it, decide what matters, report it in Nova's voice. **Read-only. No drafting sent, no sending.**
- Surface the result in the app in Nova's voice: "here's what came in." Plain is fine.
- Test it live yourself: one real email in, Nova reports it. Prove it before you call it done.

## Defaults — don't ask, just use these

- Mail worker sends nothing. Read-only this run. Drafting and sending stay off until Sam says otherwise.
- Model driving the mail worker: **Ollama** (keeps it free, self-contained, no new key). Swappable to Claude later.

## When you're done

Report once, short: what's live, that you tested it, and the one allow-link for Sam. Nothing else until then.
