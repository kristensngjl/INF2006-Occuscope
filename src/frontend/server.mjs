import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
const assets = new Set(['index.html','styles.css','app.js','data.js','model.js','bookings.js','login.css']);
const types = {'.html':'text/html','.css':'text/css','.js':'text/javascript'};
http.createServer(async (req,res) => {
  const url = new URL(req.url,'http://localhost');
  const writeRoute = /^\/api\/(chat|auth\/(login|logout)|bookings|bookings\/[a-f0-9]+\/cancel)$/.test(url.pathname);
  if(req.method !== 'GET' && !(req.method === 'POST' && writeRoute)) {res.writeHead(405); return res.end();}
  if(req.method === 'POST' && url.pathname !== '/api/chat') {
    const expectedOrigin = process.env.PUBLIC_ORIGIN || `http://${req.headers.host}`;
    if(req.headers['x-occuscope-request'] !== '1' || (req.headers.origin && req.headers.origin !== expectedOrigin)) {
      res.writeHead(403,{'Content-Type':'application/json'});return res.end(JSON.stringify({detail:'Request origin rejected.'}));
    }
  }
  try {
    if(url.pathname.startsWith('/api/')) {
      const upstream = new URL(process.env.API_ORIGIN || 'http://127.0.0.1:8000');
      upstream.pathname = url.pathname.slice(4); upstream.search = url.search;
      let body;
      if(req.method==='POST'){
        const chunks=[];let size=0;
        for await(const chunk of req){size+=chunk.length;if(size>8192){res.writeHead(413);return res.end('Request too large');}chunks.push(chunk);}
        body=Buffer.concat(chunks);
      }
      const response = await fetch(upstream,{method:req.method,body,headers:{...(body?{'Content-Type':'application/json'}:{}),...(req.headers.cookie?{'Cookie':req.headers.cookie}:{}),...(req.headers['x-occuscope-request']==='1'?{'X-Occuscope-Request':'1'}:{})},signal:AbortSignal.timeout(25000)});
      const headers={'Content-Type':'application/json','Cache-Control':'no-store'};
      const cookie=response.headers.get('set-cookie');if(cookie)headers['Set-Cookie']=cookie;
      res.writeHead(response.status,headers);
      return res.end(await response.text());
    }
    const name = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
    let file;
    if(assets.has(name)) file = path.join(root,name);
    else {res.writeHead(404); return res.end('Not found');}
    const content = await readFile(file);
    res.writeHead(200,{'Content-Type':`${types[path.extname(file)]}; charset=utf-8`,'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'});
    res.end(content);
  } catch(error) {res.writeHead(503,{'Content-Type':'application/json'}); res.end(JSON.stringify({detail:'Data unavailable. Start the API on port 8000.'}));}
}).listen(Number(process.env.PORT || 5173),'127.0.0.1',()=>console.log('Occuscope: http://127.0.0.1:'+(process.env.PORT || 5173)));
