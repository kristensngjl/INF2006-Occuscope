import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
const assets = new Set(['index.html','styles.css','app.js','data.js','model.js']);
const types = {'.html':'text/html','.css':'text/css','.js':'text/javascript'};
http.createServer(async (req,res) => {
  const url = new URL(req.url,'http://localhost');
  if(req.method !== 'GET') {res.writeHead(405); return res.end();}
  try {
    if(url.pathname.startsWith('/api/')) {
      const upstream = new URL(process.env.API_ORIGIN || 'http://127.0.0.1:8000');
      upstream.pathname = url.pathname.slice(4); upstream.search = url.search;
      const response = await fetch(upstream,{signal:AbortSignal.timeout(12000)});
      res.writeHead(response.status,{'Content-Type':'application/json'});
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
