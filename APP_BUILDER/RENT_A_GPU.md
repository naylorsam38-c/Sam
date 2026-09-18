# Renting a GPU for layer three

Layer three is the only place in the whole system a model is touched. It refuses
to run until three settings are filled, and it names the missing one rather than
falling back to anything.

---

## What layer three actually sends

A POST to whatever address you give it, with this body:

```json
{
  "model": "<LAYER3_MODEL>",
  "max_tokens": 4000,
  "messages": [{"role": "user", "content": "<the gap record>"}]
}
```

and this header:

```
Authorization: Bearer <LAYER3_CREDENTIAL>
```

That is the standard chat-completions shape. Nothing in it is tied to any
particular provider.

---

## So what do you need to rent

**A box that serves an HTTP API, not a bare GPU.** The hardware is not the part
that matters here — the server sitting in front of it is.

A rented GPU running vLLM, Ollama, llama.cpp's server, or anything else that
exposes a chat-completions endpoint will work. A bare GPU with nothing listening
on it will not.

Three things to check before you pay for anything:

1. It exposes an HTTP endpoint you can reach from outside the box.
2. That endpoint speaks the chat-completions shape above.
3. It accepts a bearer token, or lets you set one.

---

## Where the three settings go

Open `pack/5_chain/layer3_gap.py`. They are at the top, in the config block,
above any logic.

```python
LAYER3_ENDPOINT = ""      # the box's address, e.g. http://1.2.3.4:8000/v1/chat/completions
LAYER3_MODEL = ""         # the model you loaded onto it
LAYER3_CREDENTIAL = ""    # the bearer token
```

If the box is open on your own network with no token, put a placeholder in
`LAYER3_CREDENTIAL` rather than leaving it empty — empty means "not set", and
layer three will refuse.

The credential is pasted there and nowhere else. Not a file, not a command line
argument, and it is never printed.

---

## Proving it before you trust it

```
cd pack/5_chain
python layer3_gap.py <a-run-that-failed>
```

If the settings are wrong you get `HELD`, naming the setting. If the endpoint
cannot be reached you get a discarded candidate with the real reason. Neither
fabricates anything.

When it works you will see a numbered gap record written **before** any model is
called, then several candidates generated across different framings, then a
winner judged by a script driving the real system — not by the model's opinion of
its own work.

The winner is held for your approval. It is never numbered onto the shelf
automatically, because part numbers are permanent.

---

## What this unblocks

Seven of the twenty-two audit checks cover layer three and have never fired,
because no run has ever entered it. A working endpoint fires them against real
data for the first time.

It also unblocks layer two. Its failure-pattern map is empty, and correctly so —
an entry is only added after layer three has built a part, the part has been
approved onto the shelf, and the failure it fixes has been seen for real. Layer
three is the thing that starts filling it.
