/* Command Desk — front end wired to the live backend contract:
   POST /commanddesk/chat { avatar, theme, agent, message }
   GET  /commanddesk/agents -> [{id:"hub"}, ...]
   Nova is home; entering an agent turns the whole page into that room.
   No fake data: rooms come from the real roster; replies come from the real backend. */

const C = window.COMMAND_DESK_CONFIG || {};
const avatars = { nova:"Nova", halo:"Halo", gaia:"Gaia" };
const themes = {
  gunmetal:{name:"Gunmetal",a:"#1a1c20",b:"#050607",c:"#b9c0c7",g:"rgba(94,104,114,.45)"},
  volcano:{name:"Volcano",a:"#251006",b:"#050201",c:"#ff7a22",g:"rgba(227,74,18,.5)"},
  platinum:{name:"Platinum",a:"#24272b",b:"#050607",c:"#e8ebef",g:"rgba(197,205,213,.48)"}
};

const $ = s => document.querySelector(s);
const el = {
  clock:$("#clock"), date:$("#date"),
  avatarBase:$("#avatarBase"), avatarBlink:$("#avatarBlink"), avatarMouth:$("#avatarMouth"),
  avatarAccessibleName:$("#avatarAccessibleName"), avatarBtn:$("#avatarBtn"),
  state:$("#stateLabel"), agent:$("#agentLabel"),
  appearance:$("#appearance"), dialog:$("#appearanceDialog"), grid:$("#appearanceGrid"), apply:$("#apply"),
  transcript:$("#transcript"), close:$("#closeTranscript"), heard:$("#heard"), reply:$("#reply"),
  homeView:$("#homeView"), roomView:$("#roomView"), dock:$("#dock"),
  roomBack:$("#roomBack"), roomAddApp:$("#roomAddApp"), roomTitle:$("#roomTitle"),
  roomStatus:$("#roomStatus"), roomApps:$("#roomApps"), roomTranscript:$("#roomTranscript"),
  roomInput:$("#roomInput"), roomMic:$("#roomMic"), roomSend:$("#roomSend"),
  roomSwitch:$("#roomSwitch"), roomSwitchBtn:$("#roomSwitchBtn"), roomSwitchMenu:$("#roomSwitchMenu"),
  bubbleTray:$("#bubbleTray"),
  roomDialog:$("#roomDialog"), newRoomName:$("#newRoomName"), agentPicker:$("#agentPicker"),
  teamToggle:$("#teamToggle"), createRoom:$("#createRoom"),
  appDialog:$("#appDialog"), newAppName:$("#newAppName"), newAppUrl:$("#newAppUrl"), createApp:$("#createApp")
};

const store = {
  get(k, d){ try { const v = localStorage.getItem(k); return v==null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch {} }
};

let S = {
  avatar: store.get("cd.avatar","nova"),
  sessions: store.get("cd.sessions",{}),
  theme: store.get("cd.theme","platinum"),
  mode:"idle",
  agents: [],                 // real roster [{id}]
  rooms: [],                  // built-ins + spawned
  spawned: store.get("cd.rooms", []),
  messages: store.get("cd.messages", {}),
  pending: store.get("cd.pending", {}),
  activeRoomId: null,         // null = home
  recognition: null, recTarget:"home",
  blinkTimer:null, mouthTimer:null,
  availableFrames:{ blink:false, mouth:[] },
  pick:{ selected:new Set(), lead:null }
};

/* ---------- clock ---------- */
function clock(){
  const n = new Date();
  if(el.clock) el.clock.textContent = n.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",hour12:false});
  if(el.date) el.date.textContent = n.toLocaleDateString("en-AU",{weekday:"short",day:"numeric",month:"short"}).toUpperCase();
}
clock(); setInterval(clock,1000);

/* ---------- avatar / face engine (preserved) ---------- */
function appearance(a,t,save=true){
  S.avatar=a; S.theme=t;
  document.body.dataset.avatar=a; document.body.dataset.theme=t;
  if(el.avatarBase) el.avatarBase.src=`assets/avatars/${a}.png`;
  if(el.avatarAccessibleName) el.avatarAccessibleName.textContent=avatars[a]||a;
  resetAvatarFrame(); loadAvatarFrames(a);
  if(save){ store.set("cd.avatar",a); store.set("cd.theme",t); }
}
function frameExists(src){
  return new Promise(res=>{ const i=new Image(); i.onload=()=>res(true); i.onerror=()=>res(false); i.src=src; });
}
async function loadAvatarFrames(avatar){
  stopBlinking(); stopMouthAnimation(); resetAvatarFrame();
  const blink=`assets/avatars/${avatar}_blink.png`;
  const mouth=[1,2,3,4].map(n=>`assets/avatars/${avatar}_mouth_${n}.png`);
  const bOk=await frameExists(blink);
  const mOk=await Promise.all(mouth.map(frameExists));
  if(S.avatar!==avatar) return;
  S.availableFrames={ blink:bOk, mouth:mouth.filter((_,i)=>mOk[i]) };
  if(bOk && el.avatarBlink) el.avatarBlink.src=blink;
  if(S.availableFrames.mouth.length && el.avatarMouth) el.avatarMouth.src=S.availableFrames.mouth[0];
  scheduleBlink();
  if(S.mode==="speaking") startMouthAnimation();
}
function showAvatarFrame(f){ [el.avatarBase,el.avatarBlink,el.avatarMouth].forEach(i=>i&&i.classList.remove("active")); f&&f.classList.add("active"); }
function resetAvatarFrame(){ showAvatarFrame(el.avatarBase); }
function stopBlinking(){ if(S.blinkTimer){ clearTimeout(S.blinkTimer); S.blinkTimer=null; } }
function scheduleBlink(){
  stopBlinking();
  if(!S.availableFrames.blink || S.mode==="speaking") return;
  const delay=3800+Math.random()*5200;
  S.blinkTimer=setTimeout(()=>{
    if(S.mode!=="speaking" && S.availableFrames.blink){
      showAvatarFrame(el.avatarBlink);
      setTimeout(()=>{ resetAvatarFrame(); scheduleBlink(); },90+Math.random()*55);
    } else scheduleBlink();
  }, delay);
}
function stopMouthAnimation(){ if(S.mouthTimer){ clearTimeout(S.mouthTimer); S.mouthTimer=null; } resetAvatarFrame(); }
function startMouthAnimation(){
  stopBlinking(); stopMouthAnimation();
  const frames=S.availableFrames.mouth; if(!frames.length) return;
  let prev=-1;
  const tick=()=>{
    if(S.mode!=="speaking"){ stopMouthAnimation(); scheduleBlink(); return; }
    let i=Math.floor(Math.random()*frames.length);
    if(frames.length>1 && i===prev) i=(i+1)%frames.length;
    prev=i;
    if(el.avatarMouth){ el.avatarMouth.src=frames[i]; showAvatarFrame(el.avatarMouth); }
    S.mouthTimer=setTimeout(tick,85+Math.random()*75);
  };
  tick();
}
function mode(m,label){
  S.mode=m; document.body.dataset.state=m;
  const text=label||{idle:"READY",listening:"LISTENING",thinking:"THINKING",speaking:"SPEAKING",working:"WORKING"}[m]||"READY";
  if(el.state) el.state.textContent=text;
  if(el.roomStatus) el.roomStatus.textContent=text;
  if(el.roomMic){ el.roomMic.classList.toggle("active",m==="listening"); el.roomMic.textContent=m==="listening"?"■":"●"; }
  if(m==="speaking") startMouthAnimation(); else { stopMouthAnimation(); scheduleBlink(); }
}

/* ---------- dialogs ---------- */
function openDialog(d){ if(!d) return; if(typeof d.showModal==="function") d.showModal(); else d.setAttribute("open",""); }
function closeDialog(d){ if(!d) return; if(typeof d.close==="function") d.close(); else d.removeAttribute("open"); }

function renderGrid(){
  if(!el.grid) return;
  el.grid.innerHTML="";
  Object.keys(avatars).forEach(a=>Object.keys(themes).forEach(t=>{
    const x=themes[t], b=document.createElement("button");
    b.type="button"; b.className="option"+(S.sa===a&&S.st===t?" selected":"");
    b.style.setProperty("--pa",x.a); b.style.setProperty("--pb",x.b);
    b.style.setProperty("--pc",x.c); b.style.setProperty("--pg",x.g);
    b.innerHTML=`<img src="assets/avatars/${a}.png" alt="${avatars[a]}"><strong>${avatars[a]}</strong><small>${x.name}</small>`;
    b.onclick=()=>{ S.sa=a; S.st=t; renderGrid(); };
    el.grid.appendChild(b);
  }));
}
if(el.appearance) el.appearance.onclick=()=>{ S.sa=S.avatar; S.st=S.theme; renderGrid(); el.appearance.setAttribute("aria-expanded","true"); openDialog(el.dialog); };
if(el.apply) el.apply.onclick=e=>{ e.preventDefault(); appearance(S.sa,S.st); closeDialog(el.dialog); el.appearance&&el.appearance.setAttribute("aria-expanded","false"); };
if(el.dialog) el.dialog.addEventListener("close",()=>el.appearance&&el.appearance.setAttribute("aria-expanded","false"));
if(el.avatarBtn) el.avatarBtn.onclick=()=>startVoice("home");

/* ---------- agents + rooms ---------- */
function titleCase(id){ return String(id).replace(/[_-]+/g," ").replace(/\b\w/g,m=>m.toUpperCase()); }

async function loadAgents(){
  const base=String(C.backendBaseUrl||"").replace(/\/$/,"");
  const ep=String((C.endpoints&&C.endpoints.agents)||"/agents");
  try{
    const r=await fetch(base+(ep.startsWith("/")?ep:"/"+ep));
    if(!r.ok) throw new Error("HTTP "+r.status);
    const data=await r.json();
    const list=Array.isArray(data)?data:(data.agents||[]);
    S.agents=list.map(x=>typeof x==="string"?{id:x}:{id:x.id||x.name}).filter(x=>x.id);
  }catch(e){
    S.agents=[]; // no fakes — show offline
  }
  buildRooms();
  renderDock();
  renderRoomSwitch();
}

function buildRooms(){
  const builtins=S.agents.map(a=>({ id:"agent:"+a.id, name:titleCase(a.id), agentId:a.id, builtin:true, members:[a.id], lead:a.id, apps:[] }));
  const spawned=(S.spawned||[]).map(r=>({ ...r, builtin:false, apps:r.apps||[] }));
  S.rooms=[...builtins, ...spawned];
}

function roomById(id){ return S.rooms.find(r=>r.id===id); }

/* ---------- dock (home only, real agents) ---------- */
function renderDock(){
  if(!el.dock) return;
  el.dock.innerHTML="";
  if(!S.agents.length){
    const w=document.createElement("div");
    w.className="dock-offline";
    w.textContent="No agents connected";
    el.dock.appendChild(w);
  } else {
    S.rooms.forEach(room=>{
      const b=document.createElement("button");
      b.className="dock-item"; b.dataset.room=room.id;
      const pend=S.pending[room.id]||0;
      b.innerHTML=`<span class="dock-glyph">${room.name.charAt(0).toUpperCase()}</span>`+
                  `<small>${room.name}</small>`+
                  (pend?`<span class="dock-badge">${pend}</span>`:"");
      // one click on a pending item -> bubble; double click -> enter. Plain item -> enter.
      let clickTimer=null;
      b.addEventListener("click",()=>{
        if((S.pending[room.id]||0)>0){
          if(clickTimer){ clearTimeout(clickTimer); clickTimer=null; enterRoom(room.id); return; }
          clickTimer=setTimeout(()=>{ clickTimer=null; popBubble(room.id); },240);
        } else {
          enterRoom(room.id);
        }
      });
      el.dock.appendChild(b);
    });
  }
  // + add room (spawner)
  const add=document.createElement("button");
  add.className="dock-add"; add.setAttribute("aria-label","Add room");
  add.innerHTML=`<span class="dock-glyph">＋</span><small>Add</small>`;
  add.onclick=openRoomDialog;
  el.dock.appendChild(add);
}

/* ---------- room switch dropdown (inside a room) ---------- */
function renderRoomSwitch(){
  if(!el.roomSwitchMenu) return;
  el.roomSwitchMenu.innerHTML="";
  S.rooms.forEach(room=>{
    const b=document.createElement("button");
    b.className="switch-item"+(room.id===S.activeRoomId?" active":"");
    b.textContent=room.name;
    b.onclick=()=>{ closeRoomSwitch(); enterRoom(room.id); };
    el.roomSwitchMenu.appendChild(b);
  });
  const home=document.createElement("button");
  home.className="switch-item switch-home"; home.textContent="‹ Home";
  home.onclick=()=>{ closeRoomSwitch(); goHome(); };
  el.roomSwitchMenu.appendChild(home);
}
function openRoomSwitch(){ if(el.roomSwitchMenu){ el.roomSwitchMenu.hidden=false; el.roomSwitchBtn&&el.roomSwitchBtn.setAttribute("aria-expanded","true"); } }
function closeRoomSwitch(){ if(el.roomSwitchMenu){ el.roomSwitchMenu.hidden=true; el.roomSwitchBtn&&el.roomSwitchBtn.setAttribute("aria-expanded","false"); } }
if(el.roomSwitchBtn) el.roomSwitchBtn.onclick=()=>{ if(el.roomSwitchMenu.hidden) { renderRoomSwitch(); openRoomSwitch(); } else closeRoomSwitch(); };

/* ---------- navigation: home <-> room ---------- */
function goHome(){
  S.activeRoomId=null;
  document.body.dataset.view="home";
  el.homeView&&el.homeView.classList.add("active");
  el.roomView&&el.roomView.classList.remove("active");
  el.dock&&(el.dock.hidden=false);
  el.roomSwitch&&(el.roomSwitch.hidden=true);
  if(el.agent) el.agent.textContent="HOME";
  mode("idle");
  renderDock();
}
function enterRoom(roomId){
  const room=roomById(roomId); if(!room) return;
  S.activeRoomId=roomId;
  S.pending[roomId]=0; store.set("cd.pending",S.pending);
  document.body.dataset.view="room";
  el.homeView&&el.homeView.classList.remove("active");
  el.roomView&&el.roomView.classList.add("active");
  el.dock&&(el.dock.hidden=true);
  el.roomSwitch&&(el.roomSwitch.hidden=false);
  closeRoomSwitch();
  if(el.roomTitle) el.roomTitle.textContent=room.name;
  renderRoomApps(room);
  renderTranscript(room);
  if(el.roomInput){ el.roomInput.placeholder=`Talk to ${leadName(room)}…`; el.roomInput.value=""; el.roomInput.focus&&setTimeout(()=>el.roomInput.focus(),50); }
  mode("idle");
}
function leadName(room){ return room.lead ? titleCase(room.lead) : room.name; }
if(el.roomBack) el.roomBack.onclick=goHome;

/* ---------- room apps ---------- */
function renderRoomApps(room){
  if(!el.roomApps) return;
  const apps=room.apps||[];
  if(!apps.length){ el.roomApps.hidden=true; el.roomApps.innerHTML=""; return; }
  el.roomApps.hidden=false;
  el.roomApps.innerHTML="";
  apps.forEach((a,idx)=>{
    const card=document.createElement("div");
    card.className="app-card";
    if(a.url){
      card.innerHTML=`<div class="app-card-head"><strong>${escapeHtml(a.name)}</strong>`+
        `<button class="app-open" data-i="${idx}">Open ↗</button></div>`+
        `<iframe class="app-frame" src="${escapeAttr(a.url)}" loading="lazy" referrerpolicy="no-referrer"></iframe>`;
    } else {
      card.innerHTML=`<div class="app-card-head"><strong>${escapeHtml(a.name)}</strong></div>`+
        `<div class="app-placeholder">No web address set. This panel is a placeholder until a backend action is wired.</div>`;
    }
    el.roomApps.appendChild(card);
  });
  el.roomApps.querySelectorAll(".app-open").forEach(btn=>{
    btn.onclick=()=>{ const a=room.apps[+btn.dataset.i]; if(a&&a.url) window.open(a.url,"_blank","noopener"); };
  });
}
if(el.roomAddApp) el.roomAddApp.onclick=()=>{ if(!S.activeRoomId) return; if(el.newAppName)el.newAppName.value=""; if(el.newAppUrl)el.newAppUrl.value=""; openDialog(el.appDialog); };
if(el.createApp) el.createApp.onclick=e=>{
  e.preventDefault();
  const room=roomById(S.activeRoomId); if(!room){ closeDialog(el.appDialog); return; }
  const name=(el.newAppName&&el.newAppName.value.trim())||"App";
  let url=(el.newAppUrl&&el.newAppUrl.value.trim())||"";
  if(url && !/^https?:\/\//i.test(url)) url="https://"+url;
  room.apps=room.apps||[]; room.apps.push({name,url});
  persistRoomApps(room);
  renderRoomApps(room);
  closeDialog(el.appDialog);
};
function persistRoomApps(room){
  if(room.builtin){
    const map=store.get("cd.builtinApps",{}); map[room.id]=room.apps; store.set("cd.builtinApps",map);
  } else {
    const i=S.spawned.findIndex(r=>r.id===room.id);
    if(i>=0){ S.spawned[i].apps=room.apps; store.set("cd.rooms",S.spawned); }
  }
}

/* ---------- transcript / messages ---------- */
function msgsFor(roomId){ return S.messages[roomId] || (S.messages[roomId]=[]); }
function renderTranscript(room){
  if(!el.roomTranscript) return;
  const list=msgsFor(room.id);
  el.roomTranscript.innerHTML="";
  if(!list.length){
    const e=document.createElement("div"); e.className="room-empty";
    e.textContent=`This is ${room.name}. Say something to ${leadName(room)}.`;
    el.roomTranscript.appendChild(e);
  }
  list.forEach(m=>{
    const row=document.createElement("div");
    row.className="msg "+(m.role==="you"?"msg-you":"msg-agent");
    const who=m.role==="you"?"You":(m.who||leadName(room));
    row.innerHTML=`<span class="msg-who">${escapeHtml(who)}</span><span class="msg-text">${escapeHtml(m.text)}</span>`;
    el.roomTranscript.appendChild(row);
  });
  el.roomTranscript.scrollTop=el.roomTranscript.scrollHeight;
}
function pushMsg(roomId, role, text, who){
  msgsFor(roomId).push({role,text,who}); store.set("cd.messages",S.messages);
}

/* ---------- backend chat (live contract) ---------- */
async function requestReply(agentId, message, sessionId){
  if(C.demoMode||!C.backendBaseUrl) throw new Error("Not connected");
  const base=String(C.backendBaseUrl).replace(/\/$/,"");
  const ep=String((C.endpoints&&C.endpoints.chat)||"/chat");
  const payload={ avatar:S.avatar, theme:S.theme, agent:agentId, message };
  if(sessionId) payload.session_id=sessionId;
  const r=await fetch(base+(ep.startsWith("/")?ep:"/"+ep),{
    method:"POST", headers:{"Content-Type":"application/json"},
    body:JSON.stringify(payload)
  });
  if(!r.ok) throw new Error("HTTP "+r.status);
  const d=await r.json();
  const replyText=String(d.reply ?? d.message ?? d.response ?? "");
  const newSessionId=d.session_id ?? d.sessionId ?? sessionId;
  return { text:replyText, sessionId:newSessionId };
}

/* send inside a room */
async function sendRoom(){
  const room=roomById(S.activeRoomId); if(!room) return;
  const text=(el.roomInput&&el.roomInput.value.trim())||"";
  if(!text) return;
  el.roomInput.value="";
  pushMsg(room.id,"you",text); renderTranscript(room);
  mode("thinking");
  try{
    const sessionId=S.sessions[room.id];
    const result=await requestReply(room.agentId, text, sessionId);
    if(result && result.sessionId){ S.sessions[room.id]=result.sessionId; store.set("cd.sessions",S.sessions); }
    const replyText=result && result.text ? result.text : String(result||"");
    pushMsg(room.id,"agent",replyText, leadName(room)); renderTranscript(room);
    speak(replyText);
  }catch(e){
    pushMsg(room.id,"agent","Not connected to the backend right now.", leadName(room));
    renderTranscript(room); mode("idle");
  }
}
if(el.roomSend) el.roomSend.onclick=sendRoom;
if(el.roomInput) el.roomInput.addEventListener("keydown",e=>{ if(e.key==="Enter") sendRoom(); });
if(el.roomMic) el.roomMic.onclick=()=>startVoice("room");

/* ---------- home voice ---------- */
function transcript(open=true){ if(!el.transcript) return; el.transcript.classList.toggle("open",open); el.transcript.setAttribute("aria-hidden",String(!open)); }
if(el.close) el.close.onclick=()=>transcript(false);

async function submitHome(msg){
  msg=msg.trim(); if(!msg){ mode("idle"); return; }
  if(el.heard) el.heard.textContent=msg;
  if(el.reply) el.reply.textContent="";
  transcript(true); mode("thinking");
  const agentId=(S.agents[0]&&S.agents[0].id)||"hub";
  try{
    const sid=S.sessions["home"];
    const result=await requestReply(agentId,msg,sid);
    if(result&&result.sessionId) S.sessions["home"]=result.sessionId;
    const replyText=(result&&result.text)?result.text:String(result||"");
    if(el.reply) el.reply.textContent=replyText;
    store.set("cd.sessions",S.sessions);
    speak(replyText);
  }catch{
    if(el.reply) el.reply.textContent="The assistant service is not connected yet.";
    mode("idle");
  }
}
function speak(txt){
  if(!("speechSynthesis"in window)||!txt){ mode("idle"); return; }
  try{ speechSynthesis.cancel(); }catch{}
  const u=new SpeechSynthesisUtterance(txt);
  u.lang=C.speechLanguage||"en-AU"; u.rate=.95; u.pitch=S.avatar==="halo"?.86:1;
  u.onstart=()=>mode("speaking"); u.onend=()=>mode("idle"); u.onerror=()=>mode("idle");
  try{ speechSynthesis.speak(u); }catch{ mode("idle"); }
}

/* one recognition, targeted at home or room */
const R=window.SpeechRecognition||window.webkitSpeechRecognition;
if(R){
  S.recognition=new R();
  S.recognition.lang=C.speechLanguage||"en-AU";
  S.recognition.interimResults=true; S.recognition.continuous=false;
  S.recognition.onstart=()=>mode("listening");
  S.recognition.onresult=e=>{
    let t=""; for(let i=e.resultIndex;i<e.results.length;i++) t+=e.results[i][0].transcript;
    if(S.recTarget==="home" && el.heard) el.heard.textContent=t;
    if(S.recTarget==="room" && el.roomInput) el.roomInput.value=t;
    if(e.results[e.results.length-1].isFinal){
      if(S.recTarget==="home") submitHome(t);
      else sendRoom();
    }
  };
  S.recognition.onerror=()=>mode("idle");
  S.recognition.onend=()=>{ if(S.mode==="listening") mode("idle"); };
}
function startVoice(target){
  S.recTarget=target;
  if(S.mode==="speaking"){ try{speechSynthesis.cancel();}catch{} mode("idle"); return; }
  if(!S.recognition){
    if(target==="home"){ if(el.heard) el.heard.textContent="Voice needs Chrome or Edge."; transcript(true); }
    return;
  }
  if(S.mode==="listening"){ S.recognition.stop(); mode("idle"); }
  else { if(target==="home"&&el.heard){el.heard.textContent="";el.reply&&(el.reply.textContent="");} S.recognition.start(); }
}

/* ---------- bubbles (results surfaced on home) ---------- */
function popBubble(roomId){
  const room=roomById(roomId); if(!room||!el.bubbleTray) return;
  const list=msgsFor(roomId);
  const last=[...list].reverse().find(m=>m.role==="agent");
  if(!last) { enterRoom(roomId); return; }
  const b=document.createElement("div");
  b.className="bubble";
  b.innerHTML=`<div class="bubble-head">${escapeHtml(leadName(room))}</div>`+
    `<div class="bubble-text">${escapeHtml(last.text)}</div>`+
    `<div class="bubble-actions"><button class="bubble-open">Open</button><button class="bubble-dismiss">Dismiss</button></div>`;
  b.querySelector(".bubble-open").onclick=()=>{ b.remove(); enterRoom(roomId); };
  b.querySelector(".bubble-dismiss").onclick=()=>b.remove();
  el.bubbleTray.prepend(b);
  S.pending[roomId]=0; store.set("cd.pending",S.pending); renderDock();
}

/* ---------- add room (spawner + team lead) ---------- */
function openRoomDialog(){
  if(el.newRoomName) el.newRoomName.value="";
  S.pick={ selected:new Set(), lead:null };
  renderAgentPicker();
  if(el.teamToggle) el.teamToggle.checked=false;
  openDialog(el.roomDialog);
}
function renderAgentPicker(){
  if(!el.agentPicker) return;
  el.agentPicker.innerHTML="";
  S.agents.forEach(a=>{
    const b=document.createElement("button");
    b.type="button";
    const sel=S.pick.selected.has(a.id);
    b.className="pick"+(sel?" selected":"")+(S.pick.lead===a.id?" lead":"");
    b.innerHTML=`<span class="pick-name">${titleCase(a.id)}</span>`+(S.pick.lead===a.id?`<span class="pick-lead">lead</span>`:"");
    b.onclick=()=>{
      const team=el.teamToggle&&el.teamToggle.checked;
      if(!team){ S.pick.selected=new Set([a.id]); S.pick.lead=a.id; }
      else {
        if(S.pick.selected.has(a.id)){ S.pick.selected.delete(a.id); if(S.pick.lead===a.id) S.pick.lead=[...S.pick.selected][0]||null; }
        else { S.pick.selected.add(a.id); if(!S.pick.lead) S.pick.lead=a.id; }
      }
      renderAgentPicker();
    };
    // long-press / right area to set lead in team mode
    b.oncontextmenu=(ev)=>{ ev.preventDefault(); if(S.pick.selected.has(a.id)){ S.pick.lead=a.id; renderAgentPicker(); } };
    el.agentPicker.appendChild(b);
  });
}
if(el.teamToggle) el.teamToggle.closest("label") && (el.teamToggle.parentElement.hidden=false);
if(el.teamToggle) el.teamToggle.onchange=()=>{ if(!el.teamToggle.checked){ const first=[...S.pick.selected][0]; S.pick.selected=new Set(first?[first]:[]); S.pick.lead=first||null; } renderAgentPicker(); };
if(el.createRoom) el.createRoom.onclick=e=>{
  e.preventDefault();
  const members=[...S.pick.selected];
  if(!members.length){ closeDialog(el.roomDialog); return; }
  const lead=S.pick.lead||members[0];
  const name=(el.newRoomName&&el.newRoomName.value.trim())|| (members.length>1?titleCase(lead)+" team":titleCase(lead));
  const room={ id:"room:"+Date.now(), name, agentId:lead, lead, members, apps:[], builtin:false };
  S.spawned.push(room); store.set("cd.rooms",S.spawned);
  buildRooms(); renderDock(); renderRoomSwitch();
  closeDialog(el.roomDialog);
  enterRoom(room.id);
};

/* ---------- utils ---------- */
function escapeHtml(s){ return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function escapeAttr(s){ return escapeHtml(s); }

/* close menus on outside click */
document.addEventListener("click",e=>{
  if(el.roomSwitch && !el.roomSwitch.contains(e.target)) closeRoomSwitch();
});

/* restore built-in apps */
(function restoreBuiltinApps(){
  const map=store.get("cd.builtinApps",{});
  Object.keys(map).forEach(id=>{ const r=roomById(id); if(r) r.apps=map[id]; });
})();

/* ---------- boot ---------- */
appearance(S.avatar,S.theme,false);
mode("idle");
goHome();
loadAgents();
