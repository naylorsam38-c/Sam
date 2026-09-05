/* Hands operator screen.
   Every button here calls the real API. The screen holds no state the
   server does not hold: after each call it re-reads the session and
   renders what the server actually says. */

const $ = (id) => document.getElementById(id);
const show = (testid, on) => document.querySelector(`[data-testid="${testid}"]`).hidden = !on;

let sessionId = null;
let pendingApproval = null;

function token() { return $("token").value.trim(); }

async function call(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: Object.assign({ "Authorization": "Bearer " + token() },
                           body ? { "Content-Type": "application/json" } : {}),
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json();
  if (!response.ok) {
    const error = $("error");
    error.textContent = `${response.status}: ${payload.error}`;
    error.hidden = false;
    throw new Error(payload.error);
  }
  $("error").hidden = true;
  return payload;
}

async function loadWorkflows() {
  try {
    const { workflows } = await call("GET", "/api/workflows");
    $("workflow").innerHTML = workflows
      .map((w) => `<option value="${w.workflow_id}">${w.name}</option>`).join("");
  } catch (err) { /* the error line already says why */ }
}

async function refresh() {
  const view = await call("GET", `/api/sessions/${sessionId}`);
  $("state").textContent = view.session.state;

  $("fields").innerHTML = view.fields.map((f) => {
    const needsValue = f.provenance === "MISSING" && !f.waived;
    const input = needsValue
      ? `<input data-testid="supply-${f.name}" data-field="${f.name}" class="supply">`
      : `<span data-testid="value-${f.name}">${f.value || ""}</span>`;
    return `<tr><td>${f.label}</td><td>${input}</td>
            <td><span class="tag ${f.provenance}" data-testid="prov-${f.name}">${f.provenance}</span></td></tr>`;
  }).join("");
  document.querySelectorAll(".supply").forEach((input) => {
    input.addEventListener("change", async () => {
      await call("POST", `/api/sessions/${sessionId}/information`,
                 { field: input.dataset.field, value: input.value });
      await refresh();
    });
  });
  show("panel-fields", view.fields.length > 0);

  pendingApproval = view.pending_approval;
  show("panel-gate", Boolean(pendingApproval));
  if (pendingApproval) {
    $("gate-payload").textContent = JSON.stringify(pendingApproval.payload, null, 2);
  }

  $("documents").innerHTML = view.documents.map((d) =>
    `<li data-testid="doc-${d.role}"><a href="/api/sessions/${sessionId}/documents/${d.id}">${d.filename}</a>
     — ${d.role}${d.attestation ? " — attested" : ""}</li>`).join("");
  $("trail").innerHTML = view.audit_trail.map((e) =>
    `<li>${e.kind}</li>`).join("");
  show("panel-result", view.documents.length > 0);
  $("finalise").hidden = !["REVIEW", "ACTION_REQUIRED"].includes(view.session.state)
                         || view.documents.filter((d) => d.role === "completed").length === 0;
}

$("start").addEventListener("click", async () => {
  const body = { workflow_id: $("workflow").value, customer: $("customer").value };
  const created = await call("POST", "/api/sessions", body);
  sessionId = created.session_id;
  document.querySelector('[data-testid="session-id"]').textContent = sessionId;
  show("panel-document", true);
  show("panel-price", true);
  show("panel-run", true);
  await refresh();
});

$("upload").addEventListener("click", async () => {
  const file = $("file").files[0];
  if (!file) return;
  const buffer = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  buffer.forEach((b) => { binary += String.fromCharCode(b); });
  await call("POST", `/api/sessions/${sessionId}/document`,
             { filename: file.name, content_base64: btoa(binary) });
  await refresh();
});

$("lock-price").addEventListener("click", async () => {
  await call("POST", `/api/sessions/${sessionId}/price`,
             { price_cents: Number($("price").value), scope: $("scope").value });
  await refresh();
});

$("execute").addEventListener("click", async () => {
  await call("POST", `/api/sessions/${sessionId}/execute`);
  await refresh();
});

$("finalise").addEventListener("click", async () => {
  await call("POST", `/api/sessions/${sessionId}/finalise`);
  await refresh();
});

async function decide(decision) {
  await call("POST", `/api/sessions/${sessionId}/approval`, {
    action: pendingApproval.action,
    payload_hash: pendingApproval.payload_hash,
    decision,
  });
  const action = pendingApproval.action;
  await call("POST", `/api/sessions/${sessionId}/${action === "sign_completed" ? "finalise" : "execute"}`);
  await refresh();
}

$("approve").addEventListener("click", () => decide("APPROVED"));
$("decline").addEventListener("click", () => decide("DECLINED"));

loadWorkflows();
$("token").addEventListener("change", loadWorkflows);
