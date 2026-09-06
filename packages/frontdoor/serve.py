#!/usr/bin/env python3
"""Design 3 — Show Me front door server."""
import argparse, json, os, subprocess, sys, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE=os.path.dirname(os.path.abspath(__file__)); WEB=os.path.join(HERE,'web'); BUILT=os.path.join(HERE,'built')
sys.path.insert(0,HERE)
import catalogue as cat
import matcher
import intake
import builder as bl
import assemble as ae
STATE={'next_port':8961,'apps':{}}; LOCK=threading.Lock()
WHO_OPTIONS=[{'value':k,'label':v['label'],'sub':v['means']} for k,v in intake.WHO_USES.items()]
LOOKS=[{'value':k,'label':v['label'],'sub':v['for'],'image':v['shot']} for k,v in intake.LOOKS.items()]
DENSITY_OPTIONS=intake.DENSITY_OPTIONS
MARK_OPTIONS=intake.MARK_OPTIONS

def _start_app(app_dir, port):
    proc=subprocess.Popen([sys.executable,'app.py'],cwd=app_dir,env=dict(os.environ,PORT=str(port)),stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    for _ in range(300):
        try: urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=1); return proc
        except Exception: time.sleep(.1)
    proc.terminate(); raise RuntimeError('the provisional app was built but did not start')

def _build(answers):
    proposal=matcher.match(answers.get('does',''))
    if proposal.not_on_shelf and not proposal.matches:
        raise intake.IntakeRefused('I cannot build that request from the catalogue.')
    if not proposal.matches:
        raise intake.IntakeRefused('I can\'t tell what you are after — which of these is closest?')
    # The provisional build is not a lock: it renders all three interfaces, and
    # no look is passed at all (intake.build_instance() no longer requires one).
    # who/density/mark/must_not are real open items -- no defaults, ever; a
    # missing one refuses here, in the same words build_instance() would use,
    # rather than silently filling one in.
    missing=[k for k in ('who','density','mark') if not answers.get(k)]
    if missing:
        raise intake.IntakeRefused(f"{missing[0]!r} has no answer; the front door does not fill it in for you.")
    if answers.get('must_not') is None:
        raise intake.IntakeRefused("'must_not' has no answer; say 'nothing' if there are no exclusions, "
                                   "but it must be answered.")
    a={'does':answers['does'],'cards':[x['id'] for x in proposal.matches],
       'who':answers['who'],'density':answers['density'],'mark':answers['mark'],
       'must_not':answers['must_not'],
       'name':answers.get('name') or proposal.matches[0]['name'],
       'boss':answers.get('boss')}
    out=answers.get('out') or os.path.join(BUILT, 'show-me-' + str(int(time.time()*1000)))
    spec,app_dir,result,filled=intake.run(a,out,port=answers.get('port',8961))
    port=answers.get('port',8961)
    proc=_start_app(app_dir,port)
    with LOCK: STATE['apps'][port]=proc
    return {'proposal':proposal.as_dict(),'name':a['name'],'port':port,'out':out,'open':f'http://127.0.0.1:{port}/',
            'looks': [f'http://127.0.0.1:{port}/ui-{x["value"]}.html' for x in LOOKS],
            'dir':out,'records':len(result['records_built']),'screens':result['screens_built'],
            'actions':len(spec['build_model']['actions_inventory']),
            'questions_shown':len(proposal.open_items)}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def sendj(self,code,obj):
        b=json.dumps(obj).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def sendtext(self,code,s,ct='text/html; charset=utf-8'):
        b=s.encode(); self.send_response(code); self.send_header('Content-Type',ct); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def body(self):
        n=int(self.headers.get('Content-Length','0') or 0); return json.loads(self.rfile.read(n) or b'{}')
    def do_GET(self):
        p=self.path.split('?')[0]
        if p in ('/','/index.html'): return self.sendtext(200,open(os.path.join(WEB,'index.html'),encoding='utf-8').read())
        if p=='/api/catalogue': return self.sendj(200,cat.as_json())
        if p=='/api/who': return self.sendj(200,{'options':WHO_OPTIONS})
        if p=='/api/looks': return self.sendj(200,{'options':LOOKS})
        if p=='/api/density': return self.sendj(200,{'options':DENSITY_OPTIONS})
        if p=='/api/mark': return self.sendj(200,{'options':MARK_OPTIONS})
        if p.startswith('/shots/'):
            f=os.path.join(WEB,'shots',os.path.basename(p));
            if not os.path.isfile(f): return self.sendj(404,{'error':'no such picture'})
            b=open(f,'rb').read(); self.send_response(200); self.send_header('Content-Type','image/png'); self.send_header('Content-Length',str(len(b))); self.end_headers(); return self.wfile.write(b)
        return self.sendj(404,{'error':'no route'})
    def do_POST(self):
        try:
            if self.path=='/api/match': return self.sendj(200,matcher.match(self.body().get('text','')).as_dict())
            if self.path=='/api/build': return self.sendj(200,_build(self.body()))
            if self.path=='/api/lock':
                a=self.body()
                if not a.get('look'): raise intake.IntakeRefused('interface not chosen at lock; choose Console, Board, or Pocket.')
                if not a.get('out'): raise intake.IntakeRefused("no build directory given to lock -- pass 'out' from /api/build's own response.")
                spec=intake.finalize_look(a['out'],a['look'])
                chosen=spec['build_model']['interface']['chosen']
                return self.sendj(200,{'locked':True,'interface':chosen,'control':'IFC-001.chosen',
                                       'note':'written for real: SPEC.json, C.02 and the served page all agree'})
            return self.sendj(404,{'error':'no route'})
        except (intake.IntakeRefused,ae.Refused,bl.BuildRefused) as e: return self.sendj(200,{'error':str(e)})
        except Exception as e: return self.sendj(500,{'error':f'{type(e).__name__}: {e}'})

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--port',type=int,default=8700); ap.add_argument('--apps-from',type=int,default=8961); args=ap.parse_args(argv)
    STATE['next_port']=args.apps_from; os.makedirs(BUILT,exist_ok=True); cat.verify(); print(f'front door on http://127.0.0.1:{args.port}')
    try: ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
    except KeyboardInterrupt:
        for p in STATE['apps'].values(): p.terminate()
if __name__=='__main__': main()
