# BRECHÓ GETRES — FINAL V24 — OFFLINE SEM DUPLICATA E SEM TELA BRANCA
# Execute: python app.py
import os, json, secrets, re, unicodedata, io, base64
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from datetime import datetime
from urllib.parse import quote_plus
from flask import Flask, request, redirect, session, render_template_string, Response, send_file, abort, g

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","brecho-g3-2026")
DATABASE_URL=os.environ.get("DATABASE_URL","").strip()



def crc16_ccitt(text):
    crc=0xFFFF
    for b in text.encode("utf-8"):
        crc ^= b << 8
        for _ in range(8):
            crc=((crc<<1)^0x1021)&0xFFFF if crc&0x8000 else (crc<<1)&0xFFFF
    return f"{crc:04X}"

def tlv(tag, value):
    value=str(value)
    return f"{tag}{len(value.encode('utf-8')):02d}{value}"

def pix_text(value, limit):
    value=unicodedata.normalize("NFKD", str(value or "")).encode("ASCII","ignore").decode()
    value=re.sub(r"[^A-Za-z0-9 .-]","",value).strip().upper()
    return value[:limit] or "BRECHO G3"

def pix_payload(chave, valor, nome="BRECHO G3", cidade="RIO DE JANEIRO", txid="***"):
    chave=str(chave or "").strip()
    if not chave: return ""
    merchant=tlv("00","BR.GOV.BCB.PIX")+tlv("01",chave)
    payload=(tlv("00","01")+tlv("26",merchant)+tlv("52","0000")+tlv("53","986"))
    if float(valor)>0: payload+=tlv("54",f"{float(valor):.2f}")
    payload+=tlv("58","BR")+tlv("59",pix_text(nome,25))+tlv("60",pix_text(cidade,15))
    payload+=tlv("62",tlv("05",pix_text(txid,25)))+"6304"
    return payload+crc16_ccitt(payload)

def qr_data_uri(text):
    try:
        import qrcode
        img=qrcode.make(text)
        b=io.BytesIO(); img.save(b,format="PNG")
        return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
    except Exception:
        return ""

CSS="""
*{box-sizing:border-box}html,body{margin:0;width:100%;min-height:100%;background:#000;color:#fff;font-family:Arial,sans-serif}body{font-size:22px}.app{width:100%;max-width:760px;min-height:100dvh;margin:auto;background:#000}header{padding:28px 16px 20px;text-align:center;border-bottom:1px solid #8a6422}.brandline{display:flex;justify-content:center;align-items:center;gap:12px}.brandicon{font-size:42px;color:#e7a92d}.logo{color:#e7a92d;font-size:34px;font-weight:900}.sub{font-size:15px;margin-top:7px;text-transform:uppercase}main{padding:22px 16px 38px}.box{background:linear-gradient(145deg,#171717,#090909);border:1px solid #8a6422;border-radius:22px;padding:20px;margin-bottom:16px}h2{font-size:36px}input,select,textarea{width:100%;padding:15px;margin:6px 0 12px;background:#1b1b1b;color:#fff;border:1px solid #66502a;border-radius:14px;font-size:18px}button,.btn{background:#e7a92d;color:#090909;border:0;border-radius:14px;padding:16px 18px;font-size:19px;font-weight:900;text-decoration:none;display:inline-block}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.card{overflow:hidden;background:#141414;border:1px solid #6e5223;border-radius:19px}.card img,.pic{width:100%;aspect-ratio:1;object-fit:cover}.pic{display:grid;place-items:center;font-size:62px;background:#222}.pad{padding:14px}.price{color:#e9bd50;font-weight:900;font-size:31px;line-height:1.15;margin-top:4px}.muted{color:#f0f0f0;font-size:19px;line-height:1.45;font-weight:600}.row{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}.danger{background:#6d1c1c;color:#fff}
.voltar-bar{margin-bottom:18px}
.voltar-btn{display:inline-flex;align-items:center;gap:10px;background:#171717;color:#e7a92d;border:1px solid #a87920;border-radius:16px;padding:16px 24px;font-size:22px;font-weight:900;text-decoration:none}
.foto-editor{margin:16px 0 20px;padding:16px;border:1px solid #8a6422;border-radius:18px;background:#0d0d0d;text-align:center}
.foto-preview{width:100%;max-height:360px;object-fit:contain;border-radius:15px;background:#181818;display:none;margin-bottom:14px}
.foto-preview.show{display:block}
.foto-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.foto-actions label,.foto-actions button{width:100%;margin:0;text-align:center;cursor:pointer}
.file-hidden{position:absolute;left:-9999px;width:1px;height:1px;opacity:0}
.prod-thumb{width:124px;height:124px;object-fit:cover;border-radius:14px;border:1px solid #8a6422;background:#222}
.prod-info{display:flex;align-items:center;gap:14px;min-width:0}
.prod-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}.prod-actions .btn{font-size:18px;padding:15px 17px}.ver-fotos{width:100%;text-align:center;margin-top:10px}
.galeria-produto{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.galeria-produto .card img{width:100%;aspect-ratio:1;object-fit:cover;cursor:pointer}
.foto-grande{position:fixed;inset:0;z-index:99999;background:rgba(0,0,0,.96);display:none;align-items:center;justify-content:center;padding:18px}
.foto-grande.aberta{display:flex}
.foto-grande img{max-width:96vw;max-height:82vh;object-fit:contain;border-radius:14px}
.foto-fechar{position:absolute;top:18px;right:18px;font-size:24px}
.foto-nav{position:absolute;top:50%;transform:translateY(-50%);font-size:34px;padding:14px 18px}
.foto-ant{left:8px}.foto-prox{right:8px}
.foto-contador{position:absolute;bottom:20px;left:0;right:0;text-align:center;font-weight:bold}
@media(max-width:480px){.foto-actions{grid-template-columns:1fr}.prod-thumb{width:112px;height:112px}.prod-info{align-items:flex-start}.prod-actions .btn{font-size:17px;padding:14px 15px}.price{font-size:29px}.muted{font-size:18px}h2{font-size:34px}}
.menu-grid{display:flex;flex-direction:column;gap:14px}.menu-card{min-height:168px;padding:24px 22px;display:flex;align-items:center;gap:22px;color:#fff;text-decoration:none;background:linear-gradient(145deg,#171717,#090909);border:1px solid #a87920;border-radius:22px}.menu-icon{width:104px;flex:0 0 104px;text-align:center;color:#e7a92d;font-size:72px;line-height:1}.menu-copy{flex:1}.menu-title{font-size:34px;font-weight:900;margin-bottom:10px}.menu-desc{font-size:20px;color:#d0d0d0;line-height:1.25}.menu-arrow{font-size:58px;color:#e7a92d;font-weight:900}.menu-badge{background:#e7a92d;color:#090909;border-radius:50%;min-width:52px;height:52px;display:grid;place-items:center;font-size:22px;font-weight:900}.diferenciais{margin-top:32px;padding:30px 12px;border-top:2px solid #8a6422;text-align:center;color:#fff;font-size:31px;font-weight:900;line-height:1.55;letter-spacing:.2px}.diferenciais b{color:#e7a92d;font-size:36px}
#splash{position:fixed;inset:0;z-index:9999;background:#000;display:flex;align-items:center;justify-content:center;transition:opacity .55s}#splash.hide{opacity:0;pointer-events:none}.splash-inner{text-align:center;padding:28px}.splash-mark{font-size:110px;line-height:1;color:#e7a92d;text-shadow:0 0 28px rgba(231,169,45,.4)}.splash-g3{font-size:80px;font-weight:900;color:#e7a92d;line-height:.9;margin-top:-18px}.splash-name{font-size:39px;font-weight:900;color:#e7a92d;margin-top:30px}.splash-sub{font-size:15px;line-height:1.5;margin-top:12px;text-transform:uppercase}.loader{width:42px;height:42px;border:4px solid #3b2c10;border-top-color:#e7a92d;border-radius:50%;margin:55px auto 14px;animation:spin .85s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}@media(max-width:480px){.logo{font-size:28px}.brandicon{font-size:34px}.sub{font-size:11px}main{padding:18px 12px 30px}.menu-card{min-height:148px;padding:20px 16px;gap:16px}.menu-icon{width:88px;flex-basis:88px;font-size:62px}.menu-title{font-size:29px}.menu-desc{font-size:17px}.menu-arrow{font-size:48px}.splash-mark{font-size:90px}.splash-g3{font-size:66px}.splash-name{font-size:33px}}
/* LEITURA GRANDE - BRECHÓ GETRES */
.prod-info b{font-size:29px!important;line-height:1.2;font-weight:900!important}
.prod-info .muted{font-size:19px!important;line-height:1.4}
.prod-info .price{font-size:31px!important}
.prod-actions .btn{font-size:18px!important;font-weight:900!important}
@media(max-width:480px){
  .prod-info b{font-size:27px!important}
  .prod-info .muted{font-size:18px!important}
  .prod-info .price{font-size:29px!important}
  .prod-actions .btn{font-size:17px!important}
}

"""

class PGCursor:
    def __init__(self, cur, lastrowid=None):
        self.cur=cur
        self.lastrowid=lastrowid
    def fetchone(self): return self.cur.fetchone()
    def fetchall(self): return self.cur.fetchall()
    def __iter__(self): return iter(self.cur)

_PG_POOL=None

def _pool():
    global _PG_POOL
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL do Supabase não está configurada no Render.")
    if _PG_POOL is None:
        _PG_POOL=ThreadedConnectionPool(
            1,6,DATABASE_URL,
            sslmode=os.environ.get("PGSSLMODE","require"),
            connect_timeout=8
        )
    return _PG_POOL

class PGConn:
    def __init__(self, raw): self.raw=raw
    def execute(self, sql, params=()):
        q=sql.strip().replace("?", "%s")
        cur=self.raw.cursor(cursor_factory=RealDictCursor)
        wants_id=bool(re.match(r"^\s*INSERT\s+INTO\s+(produtos|vendas)\b", q, re.I)) and " RETURNING " not in q.upper()
        if wants_id: q=q.rstrip().rstrip(';')+" RETURNING id"
        cur.execute(q, params or ())
        last=None
        if wants_id:
            row=cur.fetchone(); last=row["id"] if row else None
        return PGCursor(cur,last)
    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def close(self):
        try:
            from psycopg2.extensions import TRANSACTION_STATUS_IDLE
            if self.raw.get_transaction_status()!=TRANSACTION_STATUS_IDLE:
                self.raw.rollback()
            _pool().putconn(self.raw)
        except Exception:
            try:self.raw.close()
            except Exception:pass

def db():
    p=_pool()
    raw=p.getconn()
    if not raw.closed:
        return PGConn(raw)
    try:p.putconn(raw,close=True)
    except Exception:pass
    raw=psycopg2.connect(DATABASE_URL,sslmode=os.environ.get("PGSSLMODE","require"),connect_timeout=8)
    return PGConn(raw)

def init():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS produtos(
        id BIGSERIAL PRIMARY KEY,
        nome TEXT,time_nome TEXT,categoria TEXT,tamanho TEXT,estado TEXT,
        preco DOUBLE PRECISION,estoque INTEGER,imagem TEXT,descricao TEXT,
        ativo INTEGER DEFAULT 1,offline_id TEXT,
        imagem_dados BYTEA,imagem_mime TEXT
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS config(chave TEXT PRIMARY KEY,valor TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS fotos(
        id BIGSERIAL PRIMARY KEY,produto_id BIGINT,arquivo TEXT,principal INTEGER DEFAULT 0,
        dados BYTEA,mime TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS vendas(
        id BIGSERIAL PRIMARY KEY,data TEXT,total DOUBLE PRECISION,pagamento TEXT,itens TEXT,
        tipo_entrega TEXT DEFAULT 'retirada',taxa_entrega DOUBLE PRECISION DEFAULT 0,
        status TEXT DEFAULT 'ATIVO',estoque_devolvido INTEGER DEFAULT 0,
        offline_id TEXT,estoque_baixado INTEGER DEFAULT 0
    )""")
    # Migrações seguras: nunca apagam dados já existentes no Supabase.
    for sql in [
        "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS ativo INTEGER DEFAULT 1",
        "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS offline_id TEXT",
        "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS imagem_dados BYTEA",
        "ALTER TABLE produtos ADD COLUMN IF NOT EXISTS imagem_mime TEXT",
        "ALTER TABLE fotos ADD COLUMN IF NOT EXISTS dados BYTEA",
        "ALTER TABLE fotos ADD COLUMN IF NOT EXISTS mime TEXT",
        "ALTER TABLE vendas ADD COLUMN IF NOT EXISTS tipo_entrega TEXT DEFAULT 'retirada'",
        "ALTER TABLE vendas ADD COLUMN IF NOT EXISTS taxa_entrega DOUBLE PRECISION DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ATIVO'",
        "ALTER TABLE vendas ADD COLUMN IF NOT EXISTS estoque_devolvido INTEGER DEFAULT 0",
        "ALTER TABLE vendas ADD COLUMN IF NOT EXISTS offline_id TEXT",
        "ALTER TABLE vendas ADD COLUMN IF NOT EXISTS estoque_baixado INTEGER DEFAULT 0"
    ]: c.execute(sql)
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_vendas_offline_id ON vendas(offline_id) WHERE offline_id IS NOT NULL")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_produtos_offline_id ON produtos(offline_id) WHERE offline_id IS NOT NULL")
    for k,v in {"nome":"BRECHÓ GETRES","slogan":"Blusas de times nacionais e internacionais","pix":"","whatsapp":"5521976723047","cnpj":"","endereco":"","mensagem":"Obrigado pela preferência!","impressora":"android","largura_papel":"58","impressora_nome":"","impressora_ip":"","impressora_porta":"9100","cidade_pix":"RIO DE JANEIRO","taxa_entrega":"10.00","logo":""}.items():
        c.execute("INSERT INTO config(chave,valor) VALUES(?,?) ON CONFLICT(chave) DO NOTHING",(k,v))
    c.execute("DELETE FROM fotos WHERE dados IS NULL OR octet_length(dados)=0")
    c.execute("""UPDATE produtos p SET imagem=COALESCE((
        SELECT f.arquivo FROM fotos f
        WHERE f.produto_id=p.id AND f.dados IS NOT NULL AND octet_length(f.dados)>0
        ORDER BY f.principal DESC,f.id DESC LIMIT 1
    ),'') WHERE COALESCE(p.imagem,'')<>'' AND NOT EXISTS (
        SELECT 1 FROM fotos fx WHERE fx.produto_id=p.id AND fx.arquivo=p.imagem
        AND fx.dados IS NOT NULL AND octet_length(fx.dados)>0
    )""")
    c.commit(); c.close()

def migrar_nome_getres():
    c=db()
    r=c.execute("SELECT valor FROM config WHERE chave='nome'").fetchone()
    if r and str(r["valor"]).strip().upper()=="BRECHÓ G3":
        c.execute("UPDATE config SET valor='BRECHÓ GETRES' WHERE chave='nome'")
        c.commit()
    c.close()

def conf():
    # Cache por requisição: evita abrir várias conexões Supabase na mesma página.
    if hasattr(g,"_getres_conf"):
        return g._getres_conf
    c=db()
    d={x["chave"]:x["valor"] for x in c.execute("SELECT * FROM config")}
    c.close()
    g._getres_conf=d
    return d

def reparar_fotos_produto(c, produto_id=None):
    """Remove somente referências de fotos sem bytes e repara a foto principal."""
    filtro=""
    params=()
    if produto_id is not None:
        filtro=" AND produto_id=?"
        params=(produto_id,)
    c.execute("DELETE FROM fotos WHERE (dados IS NULL OR octet_length(dados)=0)"+filtro, params)
    if produto_id is not None:
        pids=[produto_id]
    else:
        pids=[r["id"] for r in c.execute("SELECT id FROM produtos").fetchall()]
    for pid in pids:
        principal=c.execute(
            "SELECT id,arquivo FROM fotos WHERE produto_id=? AND dados IS NOT NULL AND octet_length(dados)>0 "
            "ORDER BY principal DESC,id DESC LIMIT 1",(pid,)
        ).fetchone()
        if principal:
            c.execute("UPDATE fotos SET principal=CASE WHEN id=? THEN 1 ELSE 0 END WHERE produto_id=?",
                      (principal["id"],pid))
            fd=c.execute("SELECT dados,mime FROM fotos WHERE id=?",(principal["id"],)).fetchone()
            c.execute("UPDATE produtos SET imagem=?,imagem_dados=?,imagem_mime=? WHERE id=?",
                      (principal["arquivo"],
                       psycopg2.Binary(bytes(fd["dados"])) if fd and fd.get("dados") is not None else None,
                       (fd.get("mime") if fd else None) or "image/jpeg",pid))
        else:
            c.execute("UPDATE produtos SET imagem='',imagem_dados=NULL,imagem_mime=NULL WHERE id=?",(pid,))

def logo_data_uri():
    """Retorna a logo persistida no Supabase em data URI."""
    salvo=str(conf().get("logo","") or "").strip()
    return salvo if salvo.startswith("data:image/") else ""

def largura_impressao_mm(C=None):
    C=C or conf()
    try:
        mm=int(str(C.get("largura_papel","58")).strip())
    except Exception:
        mm=58
    return 76 if mm>=80 else 54

def botoes_impressao(texto_compartilhar="BRECHÓ GETRES"):
    """
    Opções de impressão sem obrigar RawBT:
    - Android padrão / qualquer serviço de impressão instalado
    - Compartilhar para app de impressão
    - RawBT opcional
    - USB/OTG e Wi‑Fi por meio do serviço/plugin Android do fabricante
    - ESC/POS genérico via compartilhamento
    """
    C=conf()
    modo=str(C.get("impressora","android") or "android")
    texto_json=json.dumps(texto_compartilhar,ensure_ascii=False)
    return f"""
    <div class='acoes-impressao'>
      <button type='button' onclick='window.print()'>🖨️ ANDROID / IMPRESSÃO PADRÃO</button>
      <button type='button' onclick='compartilharImpressao()'>📤 COMPARTILHAR PARA APP DE IMPRESSÃO</button>
      <button type='button' onclick='copiarEscPos()'>📋 COPIAR TEXTO ESC/POS</button>
      <details style='margin-top:8px;text-align:left'>
        <summary style='cursor:pointer;font-weight:bold'>Outras opções</summary>
        <p style='font-size:12px'>• RawBT: opcional, para quem já usa.</p>
        <p style='font-size:12px'>• USB/OTG: selecione um serviço de impressão Android compatível com sua impressora.</p>
        <p style='font-size:12px'>• Wi‑Fi/IP: use o serviço/plugin Android do fabricante ou um serviço ESC/POS instalado.</p>
        <p style='font-size:12px'>• Bluetooth direto: disponível quando o sistema for empacotado como app Android com acesso nativo ao Bluetooth.</p>
      </details>
    </div>
    <script>
    const TEXTO_IMPRESSAO={texto_json};
    async function compartilharImpressao(){{
      if(navigator.share){{
        try{{
          await navigator.share({{title:'BRECHÓ GETRES',text:TEXTO_IMPRESSAO}});
          return;
        }}catch(e){{}}
      }}
      try{{
        await navigator.clipboard.writeText(TEXTO_IMPRESSAO);
        alert('Conteúdo copiado. Abra seu aplicativo de impressão e cole/envie.');
      }}catch(e){{
        alert('Use ANDROID / IMPRESSÃO PADRÃO para escolher um serviço de impressão instalado.');
      }}
    }}
    async function copiarEscPos(){{
      try{{
        await navigator.clipboard.writeText(TEXTO_IMPRESSAO);
        alert('Texto copiado para uso em app ESC/POS, RawBT ou plugin da impressora.');
      }}catch(e){{
        alert('Não foi possível copiar. Use o botão de impressão padrão.');
      }}
    }}
    </script>
    """

@app.route("/logo-getres")
def logo_getres():
    uri=logo_data_uri()
    if not uri: abort(404)
    try:
        cab,b64=uri.split(",",1); mime=cab.split(";",1)[0].split(":",1)[1]
        return Response(base64.b64decode(b64),mimetype=mime,headers={"Cache-Control":"no-store, no-cache, must-revalidate"})
    except Exception:
        abort(404)

@app.route("/foto-arquivo/<path:arquivo>")
def foto_arquivo(arquivo):
    c=db(); r=c.execute("SELECT dados,mime FROM fotos WHERE arquivo=? AND dados IS NOT NULL ORDER BY principal DESC,id DESC LIMIT 1",(arquivo,)).fetchone(); c.close()
    if not r or r.get("dados") is None: abort(404)
    return Response(bytes(r["dados"]),mimetype=r.get("mime") or "image/jpeg",headers={"Cache-Control":"public, max-age=31536000, immutable"})

@app.route("/produto-foto/<int:pid>")
def produto_foto(pid):
    c=db()
    r=c.execute("SELECT imagem_dados,imagem_mime FROM produtos WHERE id=?",(pid,)).fetchone()
    if not r or r.get("imagem_dados") is None:
        r=c.execute("""SELECT dados AS imagem_dados,mime AS imagem_mime FROM fotos
                     WHERE produto_id=? AND dados IS NOT NULL AND octet_length(dados)>0
                     ORDER BY principal DESC,id DESC LIMIT 1""",(pid,)).fetchone()
        if r and r.get("imagem_dados") is not None:
            c.execute("UPDATE produtos SET imagem_dados=?,imagem_mime=? WHERE id=?",
                      (psycopg2.Binary(bytes(r["imagem_dados"])),r.get("imagem_mime") or "image/jpeg",pid))
            c.commit()
    c.close()
    if not r or r.get("imagem_dados") is None: abort(404)
    return Response(bytes(r["imagem_dados"]),mimetype=r.get("imagem_mime") or "image/jpeg",
                    headers={"Cache-Control":"public, max-age=86400"})

def page(title,body,nav=True):
    C=conf()
    path=request.path
    if path != "/":
        destino="/?menu=1"
        body=f"<div class=voltar-bar><a class=voltar-btn href='{destino}'>← VOLTAR</a></div>"+body
    logo_uri=logo_data_uri()
    logo_header=(f"<img src='{logo_uri}' alt='Logo BRECHÓ GETRES' style='width:48px;height:48px;object-fit:contain;display:block'>" if logo_uri else "<span class=brandicon>♧</span>")
    return render_template_string("""<!doctype html><html lang=pt-br><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover"><meta name=theme-color content="#000000"><link rel=manifest href="/manifest.json"><title>{{title}}</title><style>"""+CSS+"""</style></head><body><div id=netStatus style="position:fixed;z-index:999999;left:10px;right:10px;top:8px;padding:8px 12px;border-radius:12px;text-align:center;font-weight:800;font-size:13px;display:none"></div><div class=app><header><div class=brandline>"""+logo_header+"""<div class=logo>{{nome}}</div></div><div class=sub>{{slogan}}</div></header><main>"""+body+"""</main></div><script>
if("serviceWorker" in navigator){navigator.serviceWorker.register("/service-worker.js",{updateViaCache:"none"}).catch(()=>{})}
function getOfflineQueue(){try{return JSON.parse(localStorage.getItem("getres_offline_sales")||"[]")}catch(e){return []}}
function setOfflineQueue(q){localStorage.setItem("getres_offline_sales",JSON.stringify(q))}
function getOfflineHistory(){try{return JSON.parse(localStorage.getItem("getres_offline_history")||"[]")}catch(e){return []}}
function setOfflineHistory(h){localStorage.setItem("getres_offline_history",JSON.stringify(h))}
function getOfflineProducts(){try{return JSON.parse(localStorage.getItem("getres_offline_products")||"[]")}catch(e){return []}}
function setOfflineProducts(q){localStorage.setItem("getres_offline_products",JSON.stringify(q))}
function getOfflineActions(){try{return JSON.parse(localStorage.getItem("getres_offline_actions")||"[]")}catch(e){return []}}
function setOfflineActions(q){localStorage.setItem("getres_offline_actions",JSON.stringify(q))}
function queueOfflineAction(tipo,vid){
  let q=getOfflineActions();
  if(!q.some(x=>x.tipo===tipo&&Number(x.vid)===Number(vid))) q.push({tipo:tipo,vid:Number(vid),criado_em:new Date().toISOString()});
  setOfflineActions(q);showNetStatus();
}
async function syncOfflineActions(){
  if(!navigator.onLine)return; let q=getOfflineActions(); if(!q.length)return; const rest=[];
  for(const a of q){try{
    const rota=a.tipo==='confirmar'?('/confirmar-pagamento/'+a.vid):(a.tipo==='cancelar'?('/cancelar-pedido/'+a.vid):'');
    if(!rota)continue; const r=await fetch(rota,{method:'POST',redirect:'follow'}); if(!r.ok)rest.push(a);
  }catch(e){rest.push(a)}}
  setOfflineActions(rest);showNetStatus();
}
document.addEventListener('submit',function(ev){
  const f=ev.target;if(!f||navigator.onLine)return; const ac=f.getAttribute('action')||'';
  let m=ac.match(/^\/confirmar-pagamento\/(\d+)$/);
  if(m){ev.preventDefault();queueOfflineAction('confirmar',Number(m[1]));alert('Pagamento confirmado OFFLINE. A confirmação será enviada automaticamente quando a internet voltar.');location='/pedidos';return}
  m=ac.match(/^\/cancelar-pedido\/(\d+)$/);
  if(m){ev.preventDefault();queueOfflineAction('cancelar',Number(m[1]));alert('Cancelamento salvo OFFLINE. Será enviado automaticamente quando a internet voltar.');location='/pedidos'}
},true);
async function fileDataURL(f){return new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=no;r.readAsDataURL(f)})}
async function syncOfflineProducts(){
  if(!navigator.onLine)return; let q=getOfflineProducts(); if(!q.length)return; const rest=[];
  for(const p of q){try{const r=await fetch('/sync-offline-product',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});const d=await r.json();if(!(r.ok&&d.ok)){p.last_error=d.erro||'Falha ao sincronizar produto';rest.push(p)}}catch(e){rest.push(p)}}
  setOfflineProducts(rest); if(!rest.length)refreshOfflineCatalog();
}
function saveOfflineHistory(sale,status,serverId,erro){
  let h=getOfflineHistory();
  const i=h.findIndex(x=>x.offline_id===sale.offline_id);
  const item={...sale,local_status:status||sale.local_status||"PENDENTE",server_id:serverId||sale.server_id||null,last_error:erro||sale.last_error||""};
  if(i>=0)h[i]=item;else h.unshift(item);
  setOfflineHistory(h.slice(0,100));
}
function showNetStatus(){
  const el=document.getElementById("netStatus"); if(!el)return;
  const q=getOfflineQueue();
  if(!navigator.onLine){
    el.style.display="block";el.style.background="#7a1f1f";el.style.color="#fff";
    el.textContent="OFFLINE • "+q.length+" pedido(s) aguardando sincronização";
  }else if(q.length){
    el.style.display="block";el.style.background="#7a5a12";el.style.color="#fff";
    el.textContent="ONLINE • sincronizando "+q.length+" pedido(s)...";
  }else{el.style.display="none"}
}
async function refreshOfflineCatalog(){
  if(!navigator.onLine)return;
  try{
    const r=await fetch("/offline/catalogo",{cache:"no-store"});
    if(r.ok)localStorage.setItem("getres_catalogo",JSON.stringify(await r.json()));
  }catch(e){}
}
async function syncOfflineSales(){
  if(!navigator.onLine)return;
  let q=getOfflineQueue(); if(!q.length){showNetStatus();return}
  const rest=[];
  for(const sale of q){
    try{
      const r=await fetch("/sync-offline-sale",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(sale)});
      const d=await r.json();
      if(r.ok && d.ok){
        saveOfflineHistory(sale,"SINCRONIZADO",d.id||null,"");
      }else{
        sale.last_error=d.erro||"Falha ao sincronizar";rest.push(sale);
        saveOfflineHistory(sale,"PENDENTE",null,sale.last_error);
      }
    }catch(e){
      rest.push(sale);
      saveOfflineHistory(sale,"PENDENTE",null,sale.last_error||"");
    }
  }
  setOfflineQueue(rest);showNetStatus();
  if(typeof renderPedidosOffline==="function")renderPedidosOffline();
  if(rest.length===0)refreshOfflineCatalog();
}
window.addEventListener("online",()=>{showNetStatus();syncOfflineProducts();syncOfflineSales();syncOfflineActions()});
window.addEventListener("offline",showNetStatus);
document.addEventListener("DOMContentLoaded",()=>{
  showNetStatus();
  if(!navigator.onLine)return;
  const agora=Date.now(), ultimo=Number(localStorage.getItem("getres_last_sync")||0);
  if(agora-ultimo>30000){
    localStorage.setItem("getres_last_sync",String(agora));
    refreshOfflineCatalog();
    syncOfflineProducts();
    syncOfflineSales();
    syncOfflineActions();
  }
});
</script></body></html>""",title=title,nome=C["nome"],slogan=C["slogan"])

@app.route("/")
def home():
    C=conf(); whats=re.sub(r"\\D","",C.get("whatsapp","")) or "5521976723047"
    mensagem_whatsapp="""Olá! 👋 Tenho interesse nos produtos do Brechó Getres.

Gostaria de informações sobre:
1️⃣ Produtos disponíveis
2️⃣ Tamanhos e valores
3️⃣ Retirada no local
4️⃣ Envio e taxa de entrega
5️⃣ Fazer um pedido"""
    whatsapp_url=f"https://wa.me/{whats}?text={quote_plus(mensagem_whatsapp)}"
    splash_html="" if request.args.get("menu")=="1" else """<div id=splash><div class=splash-inner><div class=splash-mark>♧</div><div class=splash-g3>GETRES</div><div class=splash-name>BRECHÓ GETRES</div><div class=splash-sub>Blusas de times<br>nacionais e internacionais</div><button class="btn" style="margin-top:45px;font-size:21px;padding:18px 28px" onclick="entrarNaLoja()">ENTRAR NA LOJA</button><div class=muted style="margin-top:16px">Entre e confira nossas blusas.</div></div></div><script>function entrarNaLoja(){var x=document.getElementById('splash');if(x){x.classList.add('hide');setTimeout(function(){x.remove()},600)}}</script>"""
    body=f"""{splash_html}<div class=menu-grid>
    <a class=menu-card href='/destaques'><div class=menu-icon>🏠</div><div class=menu-copy><div class=menu-title>Início</div><div class=menu-desc>Página inicial e destaques</div></div><div class=menu-arrow>›</div></a>
    <a class=menu-card href='/produtos'><div class=menu-icon>👕</div><div class=menu-copy><div class=menu-title>Produtos</div><div class=menu-desc>Ver todos os produtos</div></div><div class=menu-arrow>›</div></a>
    <a class=menu-card href='/carrinho'><div class=menu-icon>🛒</div><div class=menu-copy><div class=menu-title>Carrinho</div><div class=menu-desc>Ver carrinho de compras</div></div><div id=homeBadge class=menu-badge>0</div><div class=menu-arrow>›</div></a>
    <a class=menu-card href='/pedidos'><div class=menu-icon>📋</div><div class=menu-copy><div class=menu-title>Pedidos</div><div class=menu-desc>Acompanhar seus pedidos</div></div><div class=menu-arrow>›</div></a>
    <a class=menu-card href='{whatsapp_url}' target='_blank'><div class=menu-icon>◉</div><div class=menu-copy><div class=menu-title>WhatsApp</div><div class=menu-desc>Fale com Brenno Luccas</div></div><div class=menu-arrow>›</div></a>
    <a class=menu-card href='/estatisticas'><div class=menu-icon>📊</div><div class=menu-copy><div class=menu-title>Estatísticas</div><div class=menu-desc>Vendas, faturamento e estoque</div></div><div class=menu-arrow>›</div></a>
    <a class=menu-card href='/config'><div class=menu-icon>⚙</div><div class=menu-copy><div class=menu-title>Configurações</div><div class=menu-desc>Configurações do app</div></div><div class=menu-arrow>›</div></a></div>
    <div class=diferenciais>
<b>✓</b> Qualidade garantida<br>
<b>✓</b> Preços justos<br>
<b>✓</b> Compra segura<br>
<b>✓</b> Retirada no local<br>
<b>✓</b> Envio com taxa
</div>
    <script>
try{{document.getElementById('homeBadge').textContent=JSON.parse(localStorage.g3cart||'[]').length}}catch(e){{}}

</script>"""
    return page("Brechó Getres",body)

@app.route("/destaques")
def destaques():
    c=db(); rows=c.execute("""SELECT p.*,
        (p.imagem_dados IS NOT NULL OR EXISTS(
          SELECT 1 FROM fotos f WHERE f.produto_id=p.id
          AND f.dados IS NOT NULL AND octet_length(f.dados)>0
        )) AS tem_foto
        FROM produtos p WHERE COALESCE(p.ativo,1)=1 ORDER BY p.id DESC""").fetchall(); c.close()
    cards=""
    for r in rows:
        tem_foto=bool(r.get("tem_foto"))
        foto=("<a href='/galeria/"+str(r["id"])+"'><img src='/produto-foto/"+str(r["id"])+"?v="+str(int(datetime.now().timestamp()))+"' alt='Ver fotos'></a>") if tem_foto else "<div class=pic>👕</div>"
        cards+=f"""<div class=card>{foto}<div class=pad><b>{r['nome']}</b><div class=muted>{r['tamanho']} • {r['estado']} • estoque {r['estoque']}</div><div class=price>R$ {r['preco']:.2f}</div><button {'disabled style="opacity:.45"' if int(r['estoque'] or 0)<=0 else ''} onclick="if({int(r['estoque'] or 0)}<=0){{alert('Produto sem estoque.');return}}let c=JSON.parse(localStorage.g3cart||'[]');let qtd=c.filter(i=>Number(i)==={r['id']}).length;if(qtd>={int(r['estoque'] or 0)}){{alert('Estoque máximo deste produto já está no carrinho.');return}}c.push({r['id']});localStorage.g3cart=JSON.stringify(c);alert('Adicionado ao carrinho')">{'+ Carrinho' if int(r['estoque'] or 0)>0 else 'SEM ESTOQUE'}</button><br><a class='btn ver-fotos' href='/galeria/{r['id']}'>📸 VER TODAS AS FOTOS</a></div></div>"""
    if not cards: cards="<div id='destaquesVazio' class=box>Nenhuma blusa cadastrada. Vá em Produtos → + Novo.</div>"
    offline_js=r"""
<script>
(function(){
  const grid=document.querySelector('.grid');
  if(!grid)return;

  function getCatalogo(){
    try{return JSON.parse(localStorage.getItem('getres_catalogo')||'[]')}catch(e){return []}
  }
  function getPendentes(){
    try{return JSON.parse(localStorage.getItem('getres_offline_products')||'[]')}catch(e){return []}
  }
  function esc(v){
    return String(v==null?'':v).replace(/[&<>"']/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function fotoProduto(p){
    if(p.imagens && p.imagens.length && p.imagens[0]) return p.imagens[0];
    if(p.imagem){
      if(String(p.imagem).startsWith('data:') || String(p.imagem).startsWith('/')) return p.imagem;
      return '/foto-arquivo/'+p.imagem;
    }
    return '';
  }
  function card(p,pendente){
    const foto=fotoProduto(p);
    const preco=Number(p.preco||0).toFixed(2);
    const img=foto ? `<img src="${esc(foto)}" alt="Produto">` : `<div class="pic">👕</div>`;
    const id=Number(p.id||0);
    const est=Number(p.estoque||0); const carrinho=id ? (est>0?`<button onclick="let c=JSON.parse(localStorage.g3cart||'[]');let qtd=c.filter(i=>Number(i)===${id}).length;if(qtd>=${est}){alert('Estoque máximo deste produto já está no carrinho.');return}c.push(${id});localStorage.g3cart=JSON.stringify(c);alert('Adicionado ao carrinho')">+ Carrinho</button>`:`<button disabled style="opacity:.45">SEM ESTOQUE</button>`) : '';
    return `<div class="card">${img}<div class="pad"><b>${esc(p.nome||'Blusa')}</b>
      <div class="muted">${esc(p.tamanho||'')} • ${esc(p.estado||'')} • estoque ${esc(p.estoque||0)}</div>
      <div class="price">R$ ${preco}</div>${pendente?'<div class="muted">⏳ Aguardando sincronização</div>':carrinho}</div></div>`;
  }

  const servidorTemProdutos = grid.querySelector('.card');
  const vazio=document.getElementById('destaquesVazio');
  const pendentes=getPendentes();

  if(servidorTemProdutos){
    if(pendentes.length) grid.insertAdjacentHTML('beforeend',pendentes.map(p=>card(p,true)).join(''));
    return;
  }

  const catalogo=getCatalogo();
  const todos=[...pendentes];
  const vistos=new Set(pendentes.map(p=>String(p.offline_id||p.id||'')));
  catalogo.forEach(p=>{
    const k=String(p.offline_id||p.id||'');
    if(!vistos.has(k)) todos.push(p);
  });

  if(todos.length){
    if(vazio)vazio.remove();
    grid.innerHTML=todos.map(p=>card(p,!!p.offline_id && !p.id)).join('');
  }
})();
</script>"""
    return page("Início","<h2>Destaques</h2><div class=grid>"+cards+"</div><br><a class=btn href='/'>← MENU PRINCIPAL</a>"+offline_js)

@app.route("/produtos")
def produtos():
    c=db(); rows=c.execute("""SELECT p.*,
        (p.imagem_dados IS NOT NULL OR EXISTS(
          SELECT 1 FROM fotos f WHERE f.produto_id=p.id
          AND f.dados IS NOT NULL AND octet_length(f.dados)>0
        )) AS tem_foto
        FROM produtos p ORDER BY p.id DESC""").fetchall(); c.close()
    x="<div class=row><h2>Produtos</h2><a class=btn href='/novo'>＋ ADICIONAR</a></div>"
    if not rows:
        x+="<div class=box>Nenhuma blusa cadastrada.</div>"
    for r in rows:
        tem_foto=bool(r.get("tem_foto"))
        foto=f"<img class=prod-thumb src='/produto-foto/{r['id']}'>" if tem_foto else "<div class='prod-thumb pic' style='font-size:36px'>👕</div>"
        x+=f"""<div class=box>
        <div class=prod-info>{foto}<div><b style='font-size:29px;line-height:1.2;font-weight:900'>{r['nome']}</b><div class=muted>{r['time_nome']} • {r['tamanho']}</div><div class=price>R$ {r['preco']:.2f}</div><div class=muted>Estoque: {r['estoque']}</div></div></div>
        <div class=prod-actions>
        <a class=btn href='/editar/{r['id']}'>✏️ DIGITAR / EDITAR</a>
        <a class=btn href='/fotos/{r['id']}'>📷 ADICIONAR FOTOS</a>
        <a class=btn href='/galeria/{r['id']}'>📸 VER TODAS AS FOTOS</a>
        <a class=btn href='/etiqueta/{r['id']}'>🏷️ ETIQUETA</a>
        {("<a class='btn danger' href='/desativar/"+str(r['id'])+"'>⛔ DESATIVAR</a>" if int(r["ativo"] if r["ativo"] is not None else 1)==1 else "<a class='btn' href='/reativar/"+str(r['id'])+"'>♻️ REATIVAR</a>")}
        <a class='btn danger' href='/excluir/{r['id']}' onclick="return confirm('Excluir definitivamente? Se já houve venda, será apenas desativado.')">🗑️ EXCLUIR</a>
        </div></div>"""
    x+="<div id=produtosOffline></div><a class=btn href='/'>← MENU PRINCIPAL</a>"
    x+="""<script>(function(){const el=document.getElementById('produtosOffline'),q=getOfflineProducts();if(!el||!q.length)return;el.innerHTML='<h3>📴 Produtos aguardando sincronização</h3>'+q.map(p=>`<div class=box><b>${p.nome}</b><div class=muted>${p.time_nome||''} • ${p.tamanho||''}</div><div class=price>R$ ${Number(p.preco||0).toFixed(2)}</div><div class=muted>⏳ Salvo neste celular</div></div>`).join('')})();</script>"""
    return page("Produtos",x)

def form_prod(r=None):
    def v(k): return str(r[k] or "") if r else ""
    atual=v("imagem")
    atual_src=f"/foto-arquivo/{atual}" if atual else ""
    show=" show" if atual else ""
    return f"""<h2>{'✏️ Editar blusa' if r else '👕 Cadastrar blusa'}</h2>
<form method=post enctype=multipart/form-data class=box id=produtoForm>
<label>Nome da blusa</label><input name=nome value="{v('nome')}" required>
<label>Time</label><input name=time_nome value="{v('time_nome')}">
<label>Categoria</label><select name=categoria><option>{v('categoria')}</option><option>Nacional</option><option>Internacional</option><option>Seleção</option><option>Retrô</option></select>
<label>Tamanho</label><input name=tamanho value="{v('tamanho')}" placeholder="P, M, G, GG...">
<label>Estado</label><select name=estado><option>{v('estado')}</option><option>Nova</option><option>Seminova</option><option>Usada</option></select>
<label>Preço</label><input name=preco value="{v('preco')}" inputmode=decimal>
<label>Estoque</label><input name=estoque type=number value="{v('estoque') or 1}">
<label>Descrição</label><textarea name=descricao>{v('descricao')}</textarea>

<div class=foto-editor>
<h3>📷 Imagem da blusa</h3>
<img id=preview class="foto-preview{show}" src="{atual_src}">
<div id=semFoto class=muted style="{'display:none' if atual else ''};padding:24px">Nenhuma imagem selecionada.</div>
<input class=file-hidden id=imagemInput type=file name=imagem accept="image/*" multiple>
<input type=hidden name=remover_imagem id=removerImagem value=0>
<div class=foto-actions>
<label class=btn for=imagemInput>📷 ADICIONAR FOTOS (ATÉ 6)</label>
<button class=danger type=button onclick=excluirPreview()>🗑️ EXCLUIR FOTO</button>
</div>
<div id=multiPreview class=galeria-produto></div><p class=muted>Selecione até 6 fotos. A primeira será a principal.</p>
</div>

<button style="width:100%;font-size:18px">💾 SALVAR BLUSA</button>
</form>
<script>
const fi=document.getElementById('imagemInput'), pv=document.getElementById('preview'), sf=document.getElementById('semFoto'), rm=document.getElementById('removerImagem');
fi.addEventListener('change',()=>{{let fs=[...(fi.files||[])];if(fs.length>6){{alert('Escolha no máximo 6 fotos.');fi.value='';return}};let mp=document.getElementById('multiPreview');mp.innerHTML='';fs.forEach(f=>{{let im=document.createElement('img');im.src=URL.createObjectURL(f);im.style='width:100%;aspect-ratio:1;object-fit:cover;border-radius:12px';mp.appendChild(im)}});if(fs[0]){{pv.src=URL.createObjectURL(fs[0]);pv.classList.add('show');sf.style.display='none';rm.value='0'}}}});
function excluirPreview(){{fi.value='';pv.removeAttribute('src');pv.classList.remove('show');sf.style.display='block';rm.value='1'}}
document.getElementById('produtoForm').addEventListener('submit',async function(ev){{
 if(navigator.onLine)return;
 ev.preventDefault();
 const fd=new FormData(this), fotos=[...(fi.files||[])].slice(0,6), imagens=[];
 for(const f of fotos) imagens.push(await fileDataURL(f));
 const p={{offline_id:'prod-'+Date.now()+'-'+Math.random().toString(16).slice(2),nome:fd.get('nome')||'',time_nome:fd.get('time_nome')||'',categoria:fd.get('categoria')||'',tamanho:fd.get('tamanho')||'',estado:fd.get('estado')||'',preco:Number(String(fd.get('preco')||'0').replace(',','.')),estoque:Number(fd.get('estoque')||0),descricao:fd.get('descricao')||'',imagens:imagens,criado_em:new Date().toISOString()}};
 let q=getOfflineProducts();q.unshift(p);setOfflineProducts(q);alert('Produto e fotos salvos OFFLINE. Serão sincronizados quando a internet voltar.');location='/produtos';
}});
</script>"""

@app.route("/novo",methods=["GET","POST"])
@app.route("/editar/<int:pid>",methods=["GET","POST"])
def produto_form(pid=None):
    c=db()
    if pid:
        reparar_fotos_produto(c,pid); c.commit()
    r=c.execute("SELECT * FROM produtos WHERE id=?",(pid,)).fetchone() if pid else None
    if request.method=="POST":
        img=r["imagem"] if r else ""; old_img=img
        if request.form.get("remover_imagem")=="1":
            img=""
            if old_img: c.execute("DELETE FROM fotos WHERE produto_id=? AND arquivo=?",(pid,old_img))
        novos=[f for f in request.files.getlist("imagem")[:6] if f and f.filename]
        novos_dados=[]
        for f in novos:
            ext=os.path.splitext(f.filename)[1].lower() or ".jpg"
            arq=secrets.token_hex(10)+ext; dados=f.read(); mime=f.mimetype or "image/jpeg"
            if dados: novos_dados.append((arq,dados,mime))
        if novos_dados: img=novos_dados[0][0]
        vals=(request.form["nome"],request.form.get("time_nome",""),request.form.get("categoria",""),request.form.get("tamanho",""),request.form.get("estado",""),float(request.form.get("preco","0").replace(",",".")),int(request.form.get("estoque","0")),img,request.form.get("descricao",""))
        if pid:
            c.execute("UPDATE produtos SET nome=?,time_nome=?,categoria=?,tamanho=?,estado=?,preco=?,estoque=?,imagem=?,descricao=? WHERE id=?",vals+(pid,)); produto_id=pid
        else:
            cur=c.execute("INSERT INTO produtos(nome,time_nome,categoria,tamanho,estado,preco,estoque,imagem,descricao) VALUES(?,?,?,?,?,?,?,?,?)",vals); produto_id=cur.lastrowid
        if novos_dados:
            reparar_fotos_produto(c,produto_id)
            existentes=int(c.execute("SELECT COUNT(*) n FROM fotos WHERE produto_id=? AND dados IS NOT NULL AND octet_length(dados)>0",(produto_id,)).fetchone()["n"] or 0)
            vagas=max(0,6-existentes)
            if vagas:
                c.execute("UPDATE fotos SET principal=0 WHERE produto_id=?",(produto_id,))
                for i,(arq,dados,mime) in enumerate(novos_dados[:vagas]):
                    c.execute("INSERT INTO fotos(produto_id,arquivo,principal,dados,mime) VALUES(?,?,?,?,?)",(produto_id,arq,1 if i==0 else 0,psycopg2.Binary(dados),mime))
                c.execute("UPDATE produtos SET imagem=?,imagem_dados=?,imagem_mime=? WHERE id=?",
                          (novos_dados[0][0],psycopg2.Binary(novos_dados[0][1]),novos_dados[0][2],produto_id))
        c.commit();c.close();return redirect("/produtos")
    out=page("Produto",form_prod(r));c.close();return out

@app.route("/desativar/<int:pid>")
def desativar(pid):
    c=db(); c.execute("UPDATE produtos SET ativo=0 WHERE id=?",(pid,)); c.commit(); c.close(); return redirect("/produtos")

@app.route("/reativar/<int:pid>")
def reativar(pid):
    c=db(); c.execute("UPDATE produtos SET ativo=1 WHERE id=?",(pid,)); c.commit(); c.close(); return redirect("/produtos")

@app.route("/excluir/<int:pid>")
def excluir(pid):
    c=db(); vendas=c.execute("SELECT itens FROM vendas").fetchall(); usado=False
    for v in vendas:
        try:
            if any(int(x.get("id",0))==pid for x in json.loads(v["itens"] or "[]")): usado=True; break
        except Exception: pass
    if usado:
        c.execute("UPDATE produtos SET ativo=0 WHERE id=?",(pid,)); c.commit(); c.close(); return redirect("/produtos")
    c.execute("DELETE FROM fotos WHERE produto_id=?",(pid,)); c.execute("DELETE FROM produtos WHERE id=?",(pid,))
    c.commit(); c.close(); return redirect("/produtos")

@app.route("/galeria/<int:pid>")
def galeria(pid):
    c=db()
    reparar_fotos_produto(c,pid); c.commit()
    p=c.execute("SELECT * FROM produtos WHERE id=?",(pid,)).fetchone()
    if not p:
        c.close()
        return "Produto não encontrado",404

    rows=c.execute("SELECT arquivo FROM fotos WHERE produto_id=? AND dados IS NOT NULL AND octet_length(dados)>0 ORDER BY principal DESC,id DESC",(pid,)).fetchall()
    arquivos=[]
    if p["imagem"]:
        arquivos.append(p["imagem"])
    for r in rows:
        arq=r["arquivo"]
        if arq and arq not in arquivos:
            arquivos.append(arq)
    c.close()

    if not arquivos:
        return page("Fotos",f"<h2>📸 {p['nome']}</h2><div class=box>Nenhuma foto cadastrada para esta blusa.</div>")

    thumbs="".join(
        f"<div class=card><img src='/foto-arquivo/{arq}' onclick='abrirFoto({i})' alt='Foto {i+1}'></div>"
        for i,arq in enumerate(arquivos)
    )
    js_arquivos=json.dumps(["/foto-arquivo/"+a for a in arquivos],ensure_ascii=False)
    body=f"""<h2>📸 {p['nome']}</h2>
    <div class=box><b>{len(arquivos)} {'foto' if len(arquivos)==1 else 'fotos'}</b>
    <div class=muted>Toque em uma imagem para visualizar em tamanho grande.</div></div>
    <div class=galeria-produto>{thumbs}</div>
    <div id=fotoGrande class=foto-grande onclick="if(event.target===this)fecharFoto()">
      <button class="btn foto-fechar" onclick=fecharFoto()>✕</button>
      <button class="btn foto-nav foto-ant" onclick="mudarFoto(-1)">‹</button>
      <img id=imagemGrande alt="Foto ampliada">
      <button class="btn foto-nav foto-prox" onclick="mudarFoto(1)">›</button>
      <div id=fotoContador class=foto-contador></div>
    </div>
    <script>
    const fotosGaleria={js_arquivos};
    let fotoAtual=0;
    function mostrarFoto(){{
      document.getElementById('imagemGrande').src=fotosGaleria[fotoAtual];
      document.getElementById('fotoContador').textContent=(fotoAtual+1)+' / '+fotosGaleria.length;
    }}
    function abrirFoto(i){{fotoAtual=i;mostrarFoto();document.getElementById('fotoGrande').classList.add('aberta')}}
    function fecharFoto(){{document.getElementById('fotoGrande').classList.remove('aberta')}}
    function mudarFoto(n){{fotoAtual=(fotoAtual+n+fotosGaleria.length)%fotosGaleria.length;mostrarFoto()}}
    </script>"""
    return page("Galeria",body)


@app.route("/api/upload-fotos/<int:pid>",methods=["POST"])
def api_upload_fotos(pid):
    c=db()
    try:
        p=c.execute("SELECT id FROM produtos WHERE id=?",(pid,)).fetchone()
        if not p:
            c.close()
            return {"ok":False,"erro":"Produto não encontrado."},404

        existentes=int(c.execute(
            "SELECT COUNT(*) n FROM fotos WHERE produto_id=? AND dados IS NOT NULL AND octet_length(dados)>0",
            (pid,)
        ).fetchone()["n"] or 0)
        vagas=max(0,6-existentes)
        if vagas<=0:
            c.close()
            return {"ok":False,"erro":"Este produto já possui 6 fotos."},400

        recebidas=[f for f in request.files.getlist("fotos") if f and f.filename]
        if not recebidas:
            c.close()
            return {"ok":False,"erro":"Nenhuma imagem chegou ao servidor."},400

        salvas=0
        for f in recebidas[:vagas]:
            dados=f.read()
            if not dados:
                continue
            mime=(f.mimetype or "image/jpeg").lower()
            if mime not in ("image/jpeg","image/png","image/webp"):
                mime="image/jpeg"
            ext=".png" if mime=="image/png" else ".webp" if mime=="image/webp" else ".jpg"
            arq=secrets.token_hex(12)+ext
            principal=1 if existentes+salvas==0 else 0

            c.execute(
                "INSERT INTO fotos(produto_id,arquivo,principal,dados,mime) VALUES(?,?,?,?,?)",
                (pid,arq,principal,psycopg2.Binary(dados),mime)
            )
            if principal:
                c.execute(
                    "UPDATE produtos SET imagem=?,imagem_dados=?,imagem_mime=? WHERE id=?",
                    (arq,psycopg2.Binary(dados),mime,pid)
                )
            salvas+=1

        if salvas==0:
            c.rollback(); c.close()
            return {"ok":False,"erro":"A imagem foi recebida, mas não pôde ser gravada."},400

        c.commit(); c.close()
        return {"ok":True,"salvas":salvas}
    except Exception as e:
        try:c.rollback()
        except Exception:pass
        try:c.close()
        except Exception:pass
        return {"ok":False,"erro":str(e)},500


@app.route("/fotos/<int:pid>",methods=["GET","POST"])
def fotos(pid):
    c=db(); p=c.execute("SELECT * FROM produtos WHERE id=?",(pid,)).fetchone()
    if not p: c.close(); return "Produto não encontrado",404
    reparar_fotos_produto(c,pid); c.commit()
    if request.method=="POST":
        fs=[f for f in request.files.getlist("fotos") if f and f.filename]
        existentes=int(c.execute("SELECT COUNT(*) n FROM fotos WHERE produto_id=? AND dados IS NOT NULL AND octet_length(dados)>0",(pid,)).fetchone()["n"] or 0); vagas=max(0,6-existentes)
        for f in fs[:vagas]:
            ext=os.path.splitext(f.filename)[1].lower() or ".jpg"; arq=secrets.token_hex(10)+ext; dados=f.read(); mime=f.mimetype or "image/jpeg"
            if not dados: continue
            tem=c.execute("SELECT 1 FROM fotos WHERE produto_id=?",(pid,)).fetchone(); principal=0 if tem else 1
            c.execute("INSERT INTO fotos(produto_id,arquivo,principal,dados,mime) VALUES(?,?,?,?,?)",(pid,arq,principal,psycopg2.Binary(dados),mime))
            if principal:
                c.execute("UPDATE produtos SET imagem=?,imagem_dados=?,imagem_mime=? WHERE id=?",
                          (arq,psycopg2.Binary(dados),mime,pid))
        c.commit(); c.close(); return redirect("/fotos/"+str(pid))
    rows=c.execute("SELECT id,produto_id,arquivo,principal FROM fotos WHERE produto_id=? AND dados IS NOT NULL AND octet_length(dados)>0 ORDER BY principal DESC,id DESC",(pid,)).fetchall(); c.close()
    cards=""
    for f in rows:
        cards+=f"""<div class=card><img src='/foto-arquivo/{f["arquivo"]}'><div class=pad>
        {'<b>⭐ Principal</b><br>' if f["principal"] else ''}
        <a class=btn href='/foto-principal/{pid}/{f["id"]}'>⭐ Principal</a>
        <a class='btn danger' href='/foto-excluir/{pid}/{f["id"]}'>🗑 Excluir</a></div></div>"""
    body=f"""<h2>📸 Fotos • G3-{pid:05d}</h2>
    <div class=box>
      <label>➕ Adicionar fotos</label>
      <input class=file-hidden id=cameraFotos type=file accept='image/*' capture='environment'>
      <input class=file-hidden id=galeriaFotos type=file accept='image/*' multiple>
      <div class=foto-actions>
        <label class=btn for=cameraFotos>📷 TIRAR FOTO</label>
        <label class=btn for=galeriaFotos>🖼️ ESCOLHER DA GALERIA</label>
      </div>
      <div id=selecionadas class=muted style='padding:16px 4px;text-align:center'>Nenhuma nova foto selecionada.</div>
      <div id=uploadStatus class=muted style='padding:8px 4px;text-align:center'></div>
      <p class=muted>Até 6 fotos. O app reduz o tamanho antes do envio para acelerar o salvamento.</p>
      <button id=salvarFotos type=button style='width:100%' disabled>💾 SALVAR FOTOS</button>
    </div>
    <div class=grid>{cards or '<div class=box>Nenhuma foto adicional.</div>'}</div>

    <script>
    const cam=document.getElementById('cameraFotos');
    const gal=document.getElementById('galeriaFotos');
    const info=document.getElementById('selecionadas');
    const statusEl=document.getElementById('uploadStatus');
    const salvar=document.getElementById('salvarFotos');
    let escolhidas=[];

    function selecionar(input){{
      escolhidas=[...(input.files||[])].slice(0,6);
      info.textContent=escolhidas.length
        ? (escolhidas.length===1?'1 foto selecionada.':escolhidas.length+' fotos selecionadas.')
        : 'Nenhuma nova foto selecionada.';
      salvar.disabled=!escolhidas.length;
    }}
    cam.addEventListener('change',()=>selecionar(cam));
    gal.addEventListener('change',()=>selecionar(gal));

    function comprimir(file){{
      return new Promise(resolve=>{{
        if(!file.type.startsWith('image/')){{resolve(file);return}}
        const img=new Image(), url=URL.createObjectURL(file);
        img.onload=()=>{{
          let w=img.naturalWidth||img.width,h=img.naturalHeight||img.height;
          const max=1400;
          if(w>max||h>max){{const s=Math.min(max/w,max/h);w=Math.round(w*s);h=Math.round(h*s)}}
          const canvas=document.createElement('canvas');
          canvas.width=w;canvas.height=h;
          canvas.getContext('2d').drawImage(img,0,0,w,h);
          URL.revokeObjectURL(url);
          canvas.toBlob(blob=>resolve(blob||file),'image/jpeg',0.8);
        }};
        img.onerror=()=>{{URL.revokeObjectURL(url);resolve(file)}};
        img.src=url;
      }});
    }}

    salvar.addEventListener('click',async()=>{{
      if(!escolhidas.length)return;
      salvar.disabled=true;
      salvar.textContent='SALVANDO...';
      try{{
        const fd=new FormData();
        for(let i=0;i<escolhidas.length;i++){{
          statusEl.textContent='Preparando foto '+(i+1)+' de '+escolhidas.length+'...';
          const blob=await comprimir(escolhidas[i]);
          fd.append('fotos',blob,'foto_'+(i+1)+'.jpg');
        }}
        statusEl.textContent='Enviando para o Supabase...';
        const r=await fetch('/api/upload-fotos/{pid}',{{method:'POST',body:fd,cache:'no-store'}});
        let d={{}};
        try{{d=await r.json()}}catch(e){{}}
        if(!r.ok||!d.ok)throw new Error(d.erro||('Erro HTTP '+r.status));
        statusEl.textContent='✅ '+d.salvas+' foto(s) salva(s) com sucesso.';
        localStorage.removeItem('getres_catalogo');
        if('caches' in window){{try{{for(const k of await caches.keys())await caches.delete(k)}}catch(e){{}}}}
        setTimeout(()=>location='/destaques?foto='+Date.now(),700);
      }}catch(e){{
        statusEl.textContent='❌ '+e.message;
        salvar.disabled=false;
        salvar.textContent='💾 SALVAR FOTOS';
      }}
    }});
    </script>"""
    return page("Fotos",body)

@app.route("/foto-principal/<int:pid>/<int:fid>")
def foto_principal(pid,fid):
    c=db(); c.execute("UPDATE fotos SET principal=0 WHERE produto_id=?",(pid,))
    f=c.execute("SELECT arquivo,dados,mime FROM fotos WHERE id=? AND produto_id=?",(fid,pid)).fetchone()
    if f:
        c.execute("UPDATE fotos SET principal=1 WHERE id=?",(fid,))
        c.execute("UPDATE produtos SET imagem=?,imagem_dados=?,imagem_mime=? WHERE id=?",
                  (f["arquivo"],psycopg2.Binary(bytes(f["dados"])) if f.get("dados") is not None else None,
                   f.get("mime") or "image/jpeg",pid))
    c.commit();c.close();return redirect("/fotos/"+str(pid))

@app.route("/foto-excluir/<int:pid>/<int:fid>")
def foto_excluir(pid,fid):
    c=db();f=c.execute("SELECT id,arquivo,principal FROM fotos WHERE id=? AND produto_id=?",(fid,pid)).fetchone()
    if f:
        c.execute("DELETE FROM fotos WHERE id=?",(fid,))
        if f["principal"]:
            n=c.execute("SELECT id,arquivo FROM fotos WHERE produto_id=? ORDER BY id DESC LIMIT 1",(pid,)).fetchone()
            if n:
                c.execute("UPDATE fotos SET principal=1 WHERE id=?",(n["id"],))
                nd=c.execute("SELECT dados,mime FROM fotos WHERE id=?",(n["id"],)).fetchone()
                c.execute("UPDATE produtos SET imagem=?,imagem_dados=?,imagem_mime=? WHERE id=?",
                          (n["arquivo"],psycopg2.Binary(bytes(nd["dados"])) if nd and nd.get("dados") is not None else None,
                           (nd.get("mime") if nd else None) or "image/jpeg",pid))
            else:
                c.execute("UPDATE produtos SET imagem='',imagem_dados=NULL,imagem_mime=NULL WHERE id=?",(pid,))
    c.commit();c.close();return redirect("/fotos/"+str(pid))

@app.route("/etiqueta/<int:pid>")
def etiqueta(pid):
    c=db();p=c.execute("SELECT * FROM produtos WHERE id=?",(pid,)).fetchone();c.close()
    if not p:return "Produto não encontrado",404
    codigo=f"GETRES-{pid:05d}"
    qr=qr_data_uri(codigo); C=conf(); largura=largura_impressao_mm(C)
    logo_uri=logo_data_uri()
    logo=(f"<img src='{logo_uri}' alt='Logo' style='width:12mm;height:12mm;object-fit:contain;display:block'>" if logo_uri else "<span style='font-size:24px;font-weight:bold'>♧</span>")
    texto=(f"BRECHÓ GETRES\\n{codigo}\\n{p['nome']}\\n{p['time_nome']}\\n"
           f"Tam: {p['tamanho']} - {p['estado']}\\nR$ {p['preco']:.2f}\\n{codigo}")
    botoes=botoes_impressao(texto)
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name=viewport content='width=device-width'>
    <style>
    @page{{size:{largura}mm auto;margin:0}}
    *{{box-sizing:border-box}}
    body{{width:{largura}mm;max-width:{largura}mm;margin:0 auto;padding:2mm;text-align:center;font:12px monospace;color:#000;background:#fff}}
    h1{{font-size:18px}}.preco{{font-size:23px;font-weight:bold}}.qr{{width:27mm;height:27mm;object-fit:contain}}
    button{{width:100%;padding:12px;margin:4px 0;font-weight:bold}}.acoes-impressao{{margin-top:8px}}
    @media print{{.acoes-impressao{{display:none!important}}body{{padding:1mm}}}}
    </style></head><body>
    <div style="display:flex;align-items:center;justify-content:center;gap:2mm;margin-bottom:2mm">{logo}<h1 style="margin:0;font-size:3.2mm;line-height:1;white-space:nowrap">BRECHÓ GETRES</h1></div>
    <b>{codigo}</b><hr>
    <b>{p["nome"]}</b><p>{p["time_nome"]}<br>Tam: {p["tamanho"]} • {p["estado"]}</p>
    <div class=preco>R$ {p["preco"]:.2f}</div><img class=qr src='{qr}'><br><b>{codigo}</b>
    {botoes}</body></html>"""


@app.route("/carrinho")
def carrinho():
    C=conf()
    try: taxa=float(str(C.get("taxa_entrega","0")).replace(",","."))
    except: taxa=0
    html="""<h2>Carrinho</h2>
<div id=itens class=box>Carregando...</div>
<div class=box>
<label>Como deseja receber?</label>
<select id=entrega onchange=atualizarTotal()>
<option value="retirada">Retirada no local — grátis</option>
<option value="entrega">Entrega — taxa R$ __TAXA__</option>
</select>
<div id=taxaInfo class=muted style="margin:8px 0 16px">Retirada no local: sem taxa.</div>
<label>Pagamento</label>
<select id=pag><option>PIX</option><option>Dinheiro</option><option>Débito</option><option>Crédito</option></select>
<button id=btnFinalizar style="width:100%" onclick=fechar()>FINALIZAR VENDA</button>
<div id=offlineInfo class=muted style="margin-top:12px"></div>
</div>
<script>
let ids=JSON.parse(localStorage.g3cart||'[]'), taxaEntrega=Number('__TAXA__'), subtotal=0;
function catalogoLocal(){try{return JSON.parse(localStorage.getItem('getres_catalogo')||'[]')}catch(e){return []}}
function dadosLocais(){
  const cat=catalogoLocal(), mapa={}; cat.forEach(x=>mapa[x.id]=x);
  return ids.map(i=>mapa[i]).filter(Boolean);
}
async function carregar(){
  try{
    const r=await fetch('/api-cart?ids='+ids.join(','),{cache:'no-store'});
    if(!r.ok)throw new Error();
    const d=await r.json();window.d=d;subtotal=d.reduce((a,x)=>a+Number(x.preco),0);render(d);
  }catch(e){
    const d=dadosLocais();window.d=d;subtotal=d.reduce((a,x)=>a+Number(x.preco),0);render(d);
    offlineInfo.textContent='Modo offline: usando catálogo salvo neste celular.';
  }
}
function render(d){
  let taxa=entrega.value==='entrega'?taxaEntrega:0,total=subtotal+taxa;
  itens.innerHTML=d.map(x=>`<p>${x.nome} <b style="float:right">R$ ${Number(x.preco).toFixed(2)}</b></p>`).join('')+
  `<hr><p>Subtotal <b style="float:right">R$ ${subtotal.toFixed(2)}</b></p>`+
  (taxa?`<p>Taxa de entrega <b style="float:right">R$ ${taxa.toFixed(2)}</b></p>`:'')+
  `<hr><b>Total: R$ ${total.toFixed(2)}</b>`;
}
function atualizarTotal(){taxaInfo.textContent=entrega.value==='entrega'?`Entrega: taxa de R$ ${taxaEntrega.toFixed(2)}`:'Retirada no local: sem taxa.';render(window.d||[])}
function uuidOffline(){return 'getres-'+Date.now()+'-'+Math.random().toString(16).slice(2)}
function salvarOffline(transactionId){
  const d=window.d||[]; if(!d.length)return alert('Não há dados do produto salvos para vender offline.');
  const qtd={}; ids.forEach(id=>qtd[Number(id)]=(qtd[Number(id)]||0)+1);
  for(const x of d){const precisa=qtd[Number(x.id)]||0,disp=Number(x.estoque||0);if(precisa>disp){alert('Estoque insuficiente para '+x.nome+'. Disponível: '+disp);return}}
  const sale={
    offline_id:transactionId||uuidOffline(),
    criado_em:new Date().toISOString(),
    pagamento:pag.value,
    tipo_entrega:entrega.value,
    taxa_entrega:entrega.value==='entrega'?taxaEntrega:0,
    total:subtotal+(entrega.value==='entrega'?taxaEntrega:0),
    itens:d.map(x=>({id:Number(x.id),nome:x.nome,tamanho:x.tamanho||'',preco:Number(x.preco)}))
  };
  let q=getOfflineQueue();q.push(sale);setOfflineQueue(q);
  saveOfflineHistory(sale,'PENDENTE',null,'');
  // baixa o estoque do catálogo local imediatamente; o servidor fará a mesma baixa uma única vez na sincronização.
  let cat=catalogoLocal(); const qtdBaixa={}; sale.itens.forEach(x=>qtdBaixa[x.id]=(qtdBaixa[x.id]||0)+1);
  cat=cat.map(x=>qtdBaixa[x.id]?({...x,estoque:Math.max(0,Number(x.estoque||0)-qtdBaixa[x.id])}):x);
  localStorage.setItem('getres_catalogo',JSON.stringify(cat));
  localStorage.removeItem('g3cart');
  showNetStatus();
  alert('Pedido salvo OFFLINE. Ele já aparece em Pedidos e será sincronizado automaticamente quando a internet voltar.');
  location='/pedidos';
}
let finalizandoVenda=false;
async function fechar(){
  if(finalizandoVenda)return;
  if(!ids.length || !window.d || !window.d.length || subtotal<=0){alert('Carrinho vazio. Adicione pelo menos uma blusa antes de finalizar.');return}
  finalizandoVenda=true;
  const btn=document.getElementById('btnFinalizar');
  if(btn){btn.disabled=true;btn.textContent='FINALIZANDO...'}
  const transactionId=uuidOffline();
  const payload={ids,pagamento:pag.value,tipo_entrega:entrega.value,taxa_entrega:entrega.value==='entrega'?taxaEntrega:0,offline_id:transactionId};
  if(!navigator.onLine){salvarOffline(transactionId);return}
  try{
    const r=await fetch('/vender',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const x=await r.json();
    if(x.ok){localStorage.removeItem('g3cart');location='/venda/'+x.id;return}
    alert(x.erro||'Não foi possível finalizar a venda.');
    finalizandoVenda=false;if(btn){btn.disabled=false;btn.textContent='FINALIZAR VENDA'}
  }catch(e){
    // Se o servidor chegou a gravar antes de a conexão cair, o mesmo transactionId
    // será usado na sincronização e o servidor reconhecerá a venda já existente.
    salvarOffline(transactionId)
  }
}
carregar();
</script>"""
    return page("Carrinho",html.replace("__TAXA__",f"{taxa:.2f}"))


@app.route("/sync-offline-product",methods=["POST"])
def sync_offline_product():
    d=request.get_json() or {}; oid=str(d.get("offline_id") or "").strip()
    if not oid or not str(d.get("nome") or "").strip(): return {"ok":False,"erro":"Produto offline inválido."},400
    c=db(); ex=c.execute("SELECT id FROM produtos WHERE offline_id=?",(oid,)).fetchone()
    if ex: c.close(); return {"ok":True,"id":ex["id"],"duplicado":True}
    try:
        imagens=d.get("imagens") or []; arquivos=[]
        for data in imagens[:6]:
            if not isinstance(data,str) or "," not in data: continue
            cab,b64=data.split(",",1); mime=cab.split(";",1)[0].split(":",1)[1] if ":" in cab else "image/jpeg"
            ext=".png" if "png" in mime else ".webp" if "webp" in mime else ".jpg"; arq=secrets.token_hex(10)+ext
            try: dados=base64.b64decode(b64)
            except Exception: continue
            if dados: arquivos.append((arq,dados,mime))
        img=arquivos[0][0] if arquivos else ""
        cur=c.execute("INSERT INTO produtos(nome,time_nome,categoria,tamanho,estado,preco,estoque,imagem,descricao,ativo,offline_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(d.get("nome",""),d.get("time_nome",""),d.get("categoria",""),d.get("tamanho",""),d.get("estado",""),float(d.get("preco") or 0),int(d.get("estoque") or 0),img,d.get("descricao",""),1,oid)); pid=cur.lastrowid
        for i,(a,dados,mime) in enumerate(arquivos): c.execute("INSERT INTO fotos(produto_id,arquivo,principal,dados,mime) VALUES(?,?,?,?,?)",(pid,a,1 if i==0 else 0,psycopg2.Binary(dados),mime))
        c.commit();c.close();return {"ok":True,"id":pid}
    except Exception as e:
        c.rollback();c.close();return {"ok":False,"erro":str(e)},400

@app.route("/offline/catalogo")
def offline_catalogo():
    c=db()
    rows=c.execute("SELECT id,nome,time_nome,categoria,tamanho,estado,preco,estoque,imagem,descricao,offline_id FROM produtos WHERE COALESCE(ativo,1)=1 ORDER BY id DESC").fetchall()
    c.close()
    return [dict(r) for r in rows]

@app.route("/sync-offline-sale",methods=["POST"])
def sync_offline_sale():
    d=request.get_json() or {}; offline_id=str(d.get("offline_id") or "").strip(); itens=d.get("itens") or []
    if not offline_id or not itens: return {"ok":False,"erro":"Pedido offline inválido."},400
    c=db(); existente=c.execute("SELECT id FROM vendas WHERE offline_id=?",(offline_id,)).fetchone()
    if existente: vid=existente["id"];c.close();return {"ok":True,"id":vid,"duplicado":True}
    try:
        total=0.0; itens_servidor=[]; contagem={}
        for item in itens:
            pid=int(item.get("id"));contagem[pid]=contagem.get(pid,0)+1
        # trava os produtos enquanto confere/baixa estoque para impedir venda duplicada concorrente
        for pid,qtd in contagem.items():
            r=c.execute("SELECT * FROM produtos WHERE id=? AND COALESCE(ativo,1)=1 FOR UPDATE",(pid,)).fetchone()
            if not r: raise ValueError(f"Produto {pid} não existe mais.")
            if int(r["estoque"] or 0)<qtd: raise ValueError(f"Estoque insuficiente para {r['nome']}.")
            for _ in range(qtd): itens_servidor.append({"id":r["id"],"nome":r["nome"],"tamanho":r["tamanho"],"preco":float(r["preco"] or 0)}); total+=float(r["preco"] or 0)
            c.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?",(qtd,pid))
        tipo=d.get("tipo_entrega","retirada"); taxa=0.0
        if tipo=="entrega":
            try: taxa=float(str(conf().get("taxa_entrega","0")).replace(",","."))
            except Exception: taxa=0.0
        total+=taxa
        cur=c.execute("INSERT INTO vendas(data,total,pagamento,itens,tipo_entrega,taxa_entrega,status,estoque_devolvido,offline_id,estoque_baixado) VALUES(?,?,?,?,?,?,?,?,?,?)",(d.get("criado_em") or datetime.now().isoformat(timespec="minutes"),total,d.get("pagamento","PIX"),json.dumps(itens_servidor,ensure_ascii=False),tipo,taxa,"AGUARDANDO_PAGAMENTO",0,offline_id,1)); vid=cur.lastrowid
        c.commit();c.close();return {"ok":True,"id":vid,"sincronizado":True}
    except psycopg2.IntegrityError:
        c.rollback(); r=c.execute("SELECT id FROM vendas WHERE offline_id=?",(offline_id,)).fetchone(); vid=r["id"] if r else None; c.close(); return {"ok":True,"id":vid,"duplicado":True}
    except Exception as e:
        c.rollback();c.close();return {"ok":False,"erro":str(e)},409

@app.route("/api-cart")
def api_cart():
    ids=[int(x) for x in request.args.get("ids","").split(",") if x.isdigit()]
    if not ids:return []
    c=db(); out=[]
    for i in ids:
        r=c.execute("SELECT id,nome,tamanho,preco,estoque FROM produtos WHERE id=?",(i,)).fetchone()
        if r:out.append(dict(r))
    c.close();return out

@app.route("/vender",methods=["POST"])
def vender():
    d=request.get_json() or {}
    offline_id=str(d.get("offline_id") or "").strip() or None
    ids=d.get("ids",[]) or []
    if not ids:
        return {"ok":False,"erro":"Carrinho vazio. Adicione pelo menos uma blusa antes de finalizar."},400
    try:
        ids=[int(x) for x in ids]
    except Exception:
        return {"ok":False,"erro":"Carrinho inválido."},400
    contagem={}
    for pid in ids: contagem[pid]=contagem.get(pid,0)+1
    c=db(); itens=[]; total=0.0
    if offline_id:
        existente=c.execute("SELECT id FROM vendas WHERE offline_id=?",(offline_id,)).fetchone()
        if existente:
            vid=existente["id"];c.close()
            return {"ok":True,"id":vid,"duplicado":True}
    try:
        # Trava, valida e reserva o estoque no momento em que a venda é finalizada.
        # Confirmar pagamento depois não baixa novamente.
        for pid,qtd in contagem.items():
            r=c.execute("SELECT * FROM produtos WHERE id=? AND COALESCE(ativo,1)=1 FOR UPDATE",(pid,)).fetchone()
            if not r or int(r["estoque"] or 0)<qtd:
                nome=r["nome"] if r else "Produto"
                raise ValueError(f"Estoque insuficiente para {nome}.")
            for _ in range(qtd):
                itens.append({"id":r["id"],"nome":r["nome"],"tamanho":r["tamanho"],"preco":float(r["preco"] or 0)})
                total+=float(r["preco"] or 0)
            c.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?",(qtd,pid))
        if not itens or total<=0: raise ValueError("Não é possível finalizar uma venda com total R$ 0,00.")
        tipo_entrega=d.get("tipo_entrega","retirada")
        taxa=0.0
        if tipo_entrega=="entrega":
            try: taxa=float(str(conf().get("taxa_entrega","0")).replace(",","."))
            except Exception: taxa=0.0
        total+=taxa
        cur=c.execute("INSERT INTO vendas(data,total,pagamento,itens,tipo_entrega,taxa_entrega,status,estoque_devolvido,offline_id,estoque_baixado) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (datetime.now().isoformat(timespec="minutes"),total,d.get("pagamento","PIX"),json.dumps(itens,ensure_ascii=False),tipo_entrega,taxa,"AGUARDANDO_PAGAMENTO",0,offline_id,1))
        vid=cur.lastrowid; c.commit(); c.close(); return {"ok":True,"id":vid}
    except psycopg2.IntegrityError:
        c.rollback()
        if offline_id:
            r=c.execute("SELECT id FROM vendas WHERE offline_id=?",(offline_id,)).fetchone()
            if r:
                vid=r["id"];c.close();return {"ok":True,"id":vid,"duplicado":True}
        c.close();return {"ok":False,"erro":"Não foi possível concluir a venda."},409
    except Exception as e:
        c.rollback(); c.close(); return {"ok":False,"erro":str(e)},409

@app.route("/venda/<int:vid>")
def venda(vid):
    c=db();v=c.execute("SELECT * FROM vendas WHERE id=?",(vid,)).fetchone();c.close()
    if not v:return "Venda não encontrada",404
    C=conf()
    if v["pagamento"]=="PIX":
        chave=C["pix"].strip()
        payload=pix_payload(chave,v["total"],C["nome"],C.get("cidade_pix","RIO DE JANEIRO"),f"GETRES{vid}")
        qr=qr_data_uri(payload) if payload else ""
        if payload:
            pix=f"""<div class=box style='text-align:center'><h3>💠 PIX QR CODE</h3>
            <p>Valor: <b>R$ {v['total']:.2f}</b></p>
            <button onclick="document.getElementById('pixqr').style.display='block'">GERAR QR CODE PIX</button>
            <div id=pixqr style='display:none;margin-top:14px'>
            <img style='width:230px;max-width:100%;background:white;padding:8px' src='{qr}'>
            <p class=muted>PIX Copia e Cola</p>
            <textarea id=copiapix readonly style='height:120px'>{payload}</textarea>
            <button onclick="navigator.clipboard.writeText(document.getElementById('copiapix').value).then(()=>alert('PIX copiado'))">COPIAR PIX</button>
            </div></div>"""
        else:
            pix="<div class=box><b>PIX não configurado.</b><p>Cadastre sua chave PIX em Configurações.</p><a class=btn href='/config'>CONFIGURAR PIX</a></div>"
    else: pix=""
    status=v["status"] or "AGUARDANDO_PAGAMENTO"
    if status=="CANCELADO":
        pix=""
        botoes="<div class='box' style='text-align:center;border-color:#8b2727'><h3>❌ PEDIDO CANCELADO</h3><p>Este pedido permanece no histórico.</p></div>"
    elif status=="PAGO":
        pix=""
        botoes=f"""<div class='box' style='text-align:center;border-color:#2f8f46'><h3>✅ PAGAMENTO CONFIRMADO</h3><p>Pedido pago e registrado no histórico.</p></div>
<a class=btn style='width:100%;text-align:center;margin-bottom:12px' href='/comprovante/{vid}'>🖨️ COMPROVANTE 58 MM</a>"""
    else:
        botoes=f"""<form method=post action='/confirmar-pagamento/{vid}' onsubmit="return confirm('Confirmar o pagamento deste pedido?')">
<button style='width:100%;font-size:18px;margin-bottom:12px' type=submit>✅ CONFIRMAR PAGAMENTO</button></form>
<a class=btn style='width:100%;text-align:center;margin-bottom:12px' href='/comprovante/{vid}'>🖨️ COMPROVANTE 58 MM</a>
<form method=post action='/cancelar-pedido/{vid}' onsubmit="return confirm('Tem certeza que deseja cancelar este pedido?')">
<button class=danger style='width:100%;font-size:17px' type=submit>❌ CANCELAR PEDIDO</button></form>"""
    entrega_info=f"<p>Taxa de entrega: R$ {v['taxa_entrega']:.2f}</p>" if v["tipo_entrega"]=="entrega" else ""
    return page("Venda",f"<h2>Venda #{vid}</h2><div class=box><div class=price>R$ {v['total']:.2f}</div><p><b>Status: {"⏳ AGUARDANDO PAGAMENTO" if status in ("ATIVO","AGUARDANDO_PAGAMENTO") else status}</b></p><p>Pagamento: {v['pagamento']}</p><p>Recebimento: {'Entrega' if v['tipo_entrega']=='entrega' else 'Retirada no local'}</p>{entrega_info}</div>{pix}{botoes}")

@app.route("/confirmar-pagamento/<int:vid>",methods=["POST"])
def confirmar_pagamento(vid):
    c=db(); v=c.execute("SELECT * FROM vendas WHERE id=? FOR UPDATE",(vid,)).fetchone()
    if not v: c.close(); return "Venda não encontrada",404
    if (v["status"] or "AGUARDANDO_PAGAMENTO") in ("ATIVO","AGUARDANDO_PAGAMENTO"):
        try: itens=json.loads(v["itens"] or "[]")
        except Exception: itens=[]
        if not int(v.get("estoque_baixado") or 0):
            contagem={}
            for item in itens:
                pid=item.get("id")
                if pid: contagem[pid]=contagem.get(pid,0)+1
            for pid,qtd in contagem.items():
                r=c.execute("SELECT estoque,nome FROM produtos WHERE id=? FOR UPDATE",(pid,)).fetchone()
                if not r or int(r["estoque"] or 0)<qtd:
                    disponivel=int(r["estoque"] or 0) if r else 0; nome=r["nome"] if r else "Produto"; c.rollback();c.close()
                    return page("Estoque insuficiente",f"<h2>⚠️ Estoque insuficiente</h2><div class=box><b>{nome}</b><p>Disponível: <b>{disponivel}</b></p><p>O pagamento não foi confirmado.</p><a class=btn href='/carrinho'>← VOLTAR AO CARRINHO</a></div>"),400
            for pid,qtd in contagem.items(): c.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?",(qtd,pid))
        c.execute("UPDATE vendas SET status='PAGO',estoque_devolvido=0,estoque_baixado=1 WHERE id=?",(vid,)); c.commit()
    c.close(); return redirect("/venda/"+str(vid))


@app.route("/cancelar-pedido/<int:vid>",methods=["POST"])
def cancelar_pedido(vid):
    c=db(); v=c.execute("SELECT * FROM vendas WHERE id=? FOR UPDATE",(vid,)).fetchone()
    if not v: c.close(); return "Venda não encontrada",404
    status_atual=v["status"] or "AGUARDANDO_PAGAMENTO"
    if status_atual!="CANCELADO":
        if int(v.get("estoque_baixado") or 0) and not int(v.get("estoque_devolvido") or 0):
            try: itens=json.loads(v["itens"] or "[]")
            except Exception: itens=[]
            contagem={}
            for item in itens:
                pid=item.get("id")
                if pid: contagem[pid]=contagem.get(pid,0)+1
            for pid,qtd in contagem.items(): c.execute("UPDATE produtos SET estoque=estoque+? WHERE id=?",(qtd,pid))
            c.execute("UPDATE vendas SET estoque_devolvido=1 WHERE id=?",(vid,))
        c.execute("UPDATE vendas SET status='CANCELADO' WHERE id=?",(vid,)); c.commit()
    c.close(); return redirect("/venda/"+str(vid))

@app.route("/comprovante/<int:vid>")
def comprovante(vid):
    c=db();v=c.execute("SELECT * FROM vendas WHERE id=?",(vid,)).fetchone();c.close();C=conf()
    if not v:return "Venda não encontrada",404
    itens=json.loads(v["itens"] or "[]")
    linhas="".join(f"<p style='overflow-wrap:anywhere;margin:5px 0'>{x['nome']} {x.get('tamanho','')}<br>R$ {float(x['preco']):.2f}</p>" for x in itens)
    logo_uri=logo_data_uri(); largura=largura_impressao_mm(C)
    logo=(f"<img src='{logo_uri}' alt='Logo' style='width:12mm;height:12mm;object-fit:contain;display:block'>" if logo_uri else "<span style='font-size:24px;font-weight:bold'>♧</span>")
    itens_txt="\\n".join(f"{x['nome']} {x.get('tamanho','')} - R$ {float(x['preco']):.2f}" for x in itens)
    entrega_txt=(f"ENTREGA - Taxa R$ {float(v['taxa_entrega'] or 0):.2f}" if v["tipo_entrega"]=="entrega" else "RETIRADA NO LOCAL")
    texto=(f"{C.get('nome','BRECHÓ GETRES')}\\n{C.get('cnpj','')}\\n{C.get('endereco','')}\\n"
           f"COMPROVANTE #{vid}\\n{itens_txt}\\n{entrega_txt}\\nTOTAL R$ {float(v['total']):.2f}\\n"
           f"{v['pagamento']}\\n{C.get('mensagem','')}")
    botoes=botoes_impressao(texto)
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name=viewport content='width=device-width'>
    <style>
    @page{{size:{largura}mm auto;margin:0}}
    *{{box-sizing:border-box}}
    body{{width:{largura}mm;max-width:{largura}mm;margin:0 auto;padding:2mm;font:12px monospace;color:#000;background:#fff;text-align:center}}
    hr{{border:0;border-top:1px dashed #000}}button{{width:100%;padding:12px;margin:4px 0;font-weight:bold}}
    .marca{{display:flex;align-items:center;justify-content:center;gap:5px}}.acoes-impressao{{margin-top:8px}}
    @media print{{.acoes-impressao{{display:none!important}}body{{padding:1mm}}}}
    </style></head><body>
    <div class=marca>{logo}<h2 style="margin:0;font-size:15px;line-height:1;white-space:nowrap">{C['nome']}</h2></div>
    <p>{C['cnpj']}<br>{C['endereco']}</p><hr><b>COMPROVANTE #{vid}</b>{linhas}<hr>
    <p>{entrega_txt}</p><h3>TOTAL R$ {float(v['total']):.2f}</h3>
    <p>{v['pagamento']}<br>{C['mensagem']}</p>{botoes}</body></html>"""


@app.route("/pedidos")
def pedidos():
    c=db();rows=c.execute("SELECT * FROM vendas ORDER BY id DESC").fetchall();c.close()
    x="<h2>Pedidos</h2><div id=pedidosOffline></div>"+''.join(f"<a class='box row' style='display:flex;color:white;text-decoration:none' href='/venda/{r['id']}'><div><b>Venda #{r['id']}</b><div class=muted>{'❌ CANCELADO' if (r['status'] or 'AGUARDANDO_PAGAMENTO')=='CANCELADO' else ('✅ PAGO' if (r['status'] or 'AGUARDANDO_PAGAMENTO')=='PAGO' else '⏳ AGUARDANDO PAGAMENTO')}</div></div><span>R$ {r['total']:.2f}</span></a>" for r in rows)
    server_orders=json.dumps([{
        "id":int(r["id"]),
        "total":float(r["total"] or 0),
        "status":str(r["status"] or "AGUARDANDO_PAGAMENTO"),
        "pagamento":str(r["pagamento"] or ""),
        "tipo_entrega":str(r["tipo_entrega"] or "retirada"),
        "taxa_entrega":float(r["taxa_entrega"] or 0),
        "data":str(r["data"] or "")
    } for r in rows],ensure_ascii=False)
    x+="<script>try{localStorage.setItem('getres_server_orders',JSON.stringify("+server_orders+"))}catch(e){}</script>"
    x+="""<script>
function renderPedidosOffline(){
  const el=document.getElementById('pedidosOffline');if(!el)return;
  const q=getOfflineQueue();
  let h=getOfflineHistory();
  // Recupera pedidos pendentes antigos para o histórico local, caso tenham sido salvos antes desta correção.
  q.forEach(p=>{if(!h.some(x=>x.offline_id===p.offline_id))h.unshift({...p,local_status:'PENDENTE'})});
  setOfflineHistory(h.slice(0,100));
  const pendentes=q.map(p=>({...p,local_status:'PENDENTE'}));
  const idsPendentes=new Set(pendentes.map(p=>p.offline_id));
  const sincronizados=h.filter(p=>!idsPendentes.has(p.offline_id) && p.local_status==='SINCRONIZADO').slice(0,5);
  const lista=[...pendentes,...sincronizados];
  const acoes=getOfflineActions();
  const avisos=acoes.map(a=>`<div class=box style="border-color:#2f8f46"><b>${a.tipo==='confirmar'?'✅ Pagamento confirmado offline':'❌ Cancelamento salvo offline'} • Venda #${a.vid}</b><div class=muted>Será sincronizado automaticamente quando a internet voltar.</div></div>`).join('');
  if(!lista.length&&!acoes.length){el.innerHTML='';return}
  el.innerHTML=avisos+lista.map((p,i)=>{
    const subtotal=(p.itens||[]).reduce((a,x)=>a+Number(x.preco||0),0);
    const total=subtotal+Number(p.taxa_entrega||0);
    const pendente=p.local_status!=='SINCRONIZADO';
    const st=pendente?'⏳ AGUARDANDO SINCRONIZAÇÃO':`✅ SINCRONIZADO${p.server_id?' • Venda #'+p.server_id:''}`;
    const erro=p.last_error?`<div class=muted style="color:#ff9b9b">${p.last_error}</div>`:'';
    const btn=pendente?`<button class=danger style="width:100%;margin-top:12px" onclick="excluirOffline('${p.offline_id}')">🗑️ EXCLUIR PEDIDO OFFLINE</button>`:'';
    return `<div class=box style="border-color:${pendente?'#a87920':'#2f8f46'}"><div class=row><div><b>📴 Pedido offline</b><div class=muted>${st}</div>${erro}</div><b>R$ ${total.toFixed(2)}</b></div>${btn}</div>`;
  }).join('');
}
function excluirOffline(offlineId){
  if(!confirm('Excluir este pedido offline antes da sincronização?'))return;
  let q=getOfflineQueue().filter(x=>x.offline_id!==offlineId);setOfflineQueue(q);
  let h=getOfflineHistory().filter(x=>x.offline_id!==offlineId);setOfflineHistory(h);
  renderPedidosOffline();showNetStatus();
}
renderPedidosOffline();
</script>"""
    return page("Pedidos",x)

@app.route("/menu")
def menu():
    return page("Menu","""<h2>Menu</h2><div class=box><a class=btn href=/config>⚙️ Configurações</a><br><br><a class=btn href=/teste>🖨️ Teste RawBT 58 mm</a></div>""")

@app.route("/estatisticas")
def estatisticas():
    c=db()
    pagos=c.execute("SELECT * FROM vendas WHERE status='PAGO' ORDER BY id DESC").fetchall()
    ativos=c.execute("SELECT COUNT(*) n FROM vendas WHERE COALESCE(status,'AGUARDANDO_PAGAMENTO') IN ('ATIVO','AGUARDANDO_PAGAMENTO')").fetchone()["n"]
    cancelados=c.execute("SELECT COUNT(*) n FROM vendas WHERE status='CANCELADO'").fetchone()["n"]
    agora=datetime.now(); hoje=agora.strftime("%Y-%m-%d"); mes=agora.strftime("%Y-%m")
    fat=sum(float(v["total"] or 0) for v in pagos)
    fat_hoje=sum(float(v["total"] or 0) for v in pagos if str(v["data"] or "").startswith(hoje))
    fat_mes=sum(float(v["total"] or 0) for v in pagos if str(v["data"] or "").startswith(mes))
    ticket=fat/len(pagos) if pagos else 0
    formas={}; vendidos={}; unidades=0
    for v in pagos:
        pg=(v["pagamento"] or "Não informado").strip()
        formas[pg]=formas.get(pg,0)+float(v["total"] or 0)
        try: itens=json.loads(v["itens"] or "[]")
        except Exception: itens=[]
        for item in itens:
            nome=item.get("nome") or "Produto"
            vendidos[nome]=vendidos.get(nome,0)+1; unidades+=1
    top=sorted(vendidos.items(),key=lambda x:(-x[1],x[0].lower()))[:5]
    produtos=c.execute("SELECT nome,estoque FROM produtos ORDER BY estoque ASC,nome").fetchall()
    estoque_total=sum(int(p["estoque"] or 0) for p in produtos)
    sem=[p["nome"] for p in produtos if int(p["estoque"] or 0)<=0]
    c.close()
    moeda=lambda v:("R$ %.2f"%v).replace(".",",")
    formas_html="".join(f"<div class='box row' style='display:flex'><b>{k}</b><span>{moeda(v)}</span></div>" for k,v in sorted(formas.items())) or "<div class=box>Nenhum pagamento confirmado ainda.</div>"
    top_html="".join(f"<div class='box row' style='display:flex'><b>{n}</b><span>{q} un.</span></div>" for n,q in top) or "<div class=box>Nenhum produto vendido ainda.</div>"
    sem_html="".join(f"<div class=box>⚠️ {n}</div>" for n in sem) or "<div class=box>✅ Nenhum produto sem estoque.</div>"
    body=f"""<h2>📊 Estatísticas</h2>
    <div class=grid>
    <div class=box><div class=muted>💰 Faturamento total</div><div class=price>{moeda(fat)}</div><small>Somente pedidos PAGOS</small></div>
    <div class=box><div class=muted>📅 Vendas de hoje</div><div class=price>{moeda(fat_hoje)}</div></div>
    <div class=box><div class=muted>🗓️ Vendas do mês</div><div class=price>{moeda(fat_mes)}</div></div>
    <div class=box><div class=muted>🎫 Ticket médio</div><div class=price>{moeda(ticket)}</div></div>
    <div class=box><b>✅ Pedidos pagos</b><div class=price>{len(pagos)}</div></div>
    <div class=box><b>⏳ Aguardando pagamento</b><div class=price>{ativos}</div></div>
    <div class=box><b>❌ Pedidos cancelados</b><div class=price>{cancelados}</div></div>
    <div class=box><b>👕 Unidades vendidas</b><div class=price>{unidades}</div></div>
    <div class=box><b>📦 Estoque atual</b><div class=price>{estoque_total}</div></div></div>
    <h3>💳 Faturamento por pagamento</h3>{formas_html}
    <h3>🏆 Produtos mais vendidos</h3>{top_html}
    <h3>⚠️ Produtos sem estoque</h3>{sem_html}"""
    return page("Estatísticas",body)

@app.route("/config",methods=["GET","POST"])
def config():
    if request.method=="POST":
        c=db()
        for k in ["nome","slogan","pix","cidade_pix","whatsapp","cnpj","endereco","mensagem",
                  "impressora","largura_papel","impressora_nome","impressora_ip","impressora_porta",
                  "taxa_entrega"]:
            c.execute("INSERT INTO config(chave,valor) VALUES(?,?) ON CONFLICT(chave) DO UPDATE SET valor=EXCLUDED.valor",
                      (k,request.form.get(k,"")))
        logo=request.files.get("logo")
        if logo and logo.filename:
            dados=logo.read(); mime=logo.mimetype or "image/png"
            if dados:
                uri="data:"+mime+";base64,"+base64.b64encode(dados).decode("ascii")
                c.execute("INSERT INTO config(chave,valor) VALUES('logo',?) ON CONFLICT(chave) DO UPDATE SET valor=EXCLUDED.valor",(uri,))
        c.commit();c.close();return redirect("/config")

    C=conf()
    labels={"nome":"Nome da loja","slogan":"Slogan","pix":"Chave PIX","cidade_pix":"Cidade do PIX",
            "whatsapp":"WhatsApp","cnpj":"CNPJ/CPF","endereco":"Endereço",
            "mensagem":"Mensagem do comprovante","taxa_entrega":"Taxa de entrega (R$)"}
    fs="".join(f"<label>{labels[k]}</label><input name={k} value='{C.get(k,'')}'>" for k in labels)

    modo=str(C.get("impressora","android") or "android")
    larg=str(C.get("largura_papel","58"))
    def selected(v): return "selected" if modo==v else ""
    sel58="selected" if larg!="80" else ""
    sel80="selected" if larg=="80" else ""

    printer=f"""
    <h3>🖨️ Impressora térmica</h3>
    <label>Método de impressão</label>
    <select name='impressora'>
      <option value='android' {selected('android')}>Android padrão — recomendado e gratuito</option>
      <option value='compartilhar' {selected('compartilhar')}>Compartilhar para aplicativo de impressão</option>
      <option value='escpos' {selected('escpos')}>ESC/POS genérico</option>
      <option value='usb' {selected('usb')}>USB / OTG via serviço Android</option>
      <option value='wifi' {selected('wifi')}>Wi‑Fi / IP via serviço/plugin Android</option>
      <option value='rawbt' {selected('rawbt')}>RawBT — opcional</option>
      <option value='bluetooth_nativo' {selected('bluetooth_nativo')}>Bluetooth direto — para futura versão Android nativa</option>
    </select>

    <label>Largura do papel</label>
    <select name='largura_papel'>
      <option value='58' {sel58}>58 mm — portátil mais comum</option>
      <option value='80' {sel80}>80 mm — recibo largo</option>
    </select>

    <label>Nome/modelo da impressora</label>
    <input name='impressora_nome' value='{C.get("impressora_nome","")}' placeholder='Ex.: XPrinter XP-P323B, Elgin, Epson...'>

    <label>IP da impressora (opcional)</label>
    <input name='impressora_ip' value='{C.get("impressora_ip","")}' placeholder='Ex.: 192.168.1.50'>

    <label>Porta ESC/POS (opcional)</label>
    <input name='impressora_porta' value='{C.get("impressora_porta","9100")}' inputmode='numeric'>

    <div class=box style='margin-top:12px'>
      <b>Compatibilidade</b>
      <p class=muted>O app não exige RawBT. Você pode usar o serviço de impressão gratuito do Android, plugin do fabricante, USB/OTG, Wi‑Fi/IP, compartilhamento ou outro app ESC/POS instalado.</p>
      <p class=muted>Bluetooth clássico direto não é universal dentro do navegador; por isso fica reservado para uma futura versão Android nativa/híbrida.</p>
    </div>

    <a class=btn href='/teste'>🧾 TESTAR IMPRESSORA</a>
    """
    return page("Configurações",
        f"<h2>Configurações</h2><form method=post enctype='multipart/form-data' class=box>{fs}{printer}"
        f"<label>Logo do BRECHÓ GETRES</label><input type=file name=logo accept='image/*'>"
        f"<p class=muted>Usada no comprovante e etiqueta. A nova logo fica salva no Supabase.</p>"
        f"<button style='width:100%'>SALVAR</button></form>")


@app.route("/teste")
def teste():
    C=conf(); largura=largura_impressao_mm(C)
    texto=(f"BRECHÓ GETRES\\nTESTE DE IMPRESSÃO\\n"
           f"Método: {C.get('impressora','android')}\\n"
           f"Papel: {C.get('largura_papel','58')} mm\\n"
           f"Modelo: {C.get('impressora_nome','')}\\n"
           f"ABCDEFGHIJKLMNOPQRSTUVWXYZ\\n0123456789\\n"
           f"Se este texto saiu completo, a largura está correta.")
    botoes=botoes_impressao(texto)
    return f"""<!doctype html><html><head><meta charset='utf-8'><meta name=viewport content='width=device-width'>
    <style>
    @page{{size:{largura}mm auto;margin:0}}
    *{{box-sizing:border-box}}
    body{{width:{largura}mm;max-width:{largura}mm;margin:0 auto;padding:2mm;text-align:center;font:12px monospace;color:#000;background:#fff}}
    button{{width:100%;padding:12px;margin:4px 0;font-weight:bold}}.acoes-impressao{{margin-top:8px}}
    @media print{{.acoes-impressao{{display:none!important}}body{{padding:1mm}}}}
    </style></head><body>
    <h2>BRECHÓ GETRES</h2>
    <p>TESTE TÉRMICO {C.get('largura_papel','58')} mm</p>
    <p>Método: {C.get('impressora','android')}</p>
    <p>{C.get('impressora_nome','')}</p>
    <p>------------------------------</p>
    <p>ABCDEFGHIJKLMNOPQRSTUVWXYZ<br>0123456789</p>
    <p>Se tudo sair completo,<br>a largura está correta.</p>
    {botoes}</body></html>"""


@app.route("/versao")
def versao():
    return {"app":"BRECHO GETRES","versao":"FINAL-FIX-2026-08-23-6-OFFLINE-IDEMPOTENTE","foto_upload":"api_dedicada","backend":"postgresql/supabase"}

@app.route("/status-banco")
def status_banco():
    c=db()
    p=c.execute("SELECT COUNT(*) n FROM produtos").fetchone()["n"]
    v=c.execute("SELECT COUNT(*) n FROM vendas").fetchone()["n"]
    f=c.execute("SELECT COUNT(*) n FROM fotos").fetchone()["n"]
    fv=c.execute("SELECT COUNT(*) n FROM fotos WHERE dados IS NOT NULL AND octet_length(dados)>0").fetchone()["n"]
    fq=c.execute("SELECT COUNT(*) n FROM fotos WHERE dados IS NULL OR octet_length(dados)=0").fetchone()["n"]
    c.close()
    return {"ok":True,"backend":"postgresql/supabase","persistente":True,"produtos":int(p),"vendas":int(v),"fotos":int(f),"fotos_validas":int(fv),"fotos_quebradas":int(fq)}

@app.route("/manifest.json")
def manifest():
    return {"name":"Brechó Getres","short_name":"GETRES","start_url":"/","display":"standalone",
            "background_color":"#080808","theme_color":"#080808"}

@app.route("/service-worker.js")
def service_worker():
    from flask import Response
    js=r"""
const CACHE='getres-final-v24-offline-sem-duplicata-sem-tela-branca';
const OFFLINE_PAGES=['/?menu=1','/destaques','/produtos','/carrinho','/pedidos'];

self.addEventListener('install',e=>{
  e.waitUntil((async()=>{
    const c=await caches.open(CACHE);
    for(const url of OFFLINE_PAGES){
      try{
        const r=await fetch(url,{cache:'no-store'});
        if(r && r.ok) await c.put(url,r.clone());
      }catch(_){}
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate',e=>{
  e.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

function pedidosOfflineHtml(){
  return `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Pedidos - BRECHÓ GETRES</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#000;color:#fff;font-family:Arial,sans-serif}
main{width:min(100%,560px);margin:auto;padding:20px 18px 80px}.brand{text-align:center;color:#e7a92d;font-weight:900;font-size:25px;margin:16px 0 24px}
h1{font-size:28px}.box{border:1px solid #8a6422;border-radius:16px;padding:16px;margin:12px 0;background:#111;color:#fff;text-decoration:none;display:block}
.row{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.muted{color:#bbb;font-size:14px;margin-top:5px}
.price{color:#e7a92d;font-size:20px;font-weight:900}.btn{display:inline-block;border:0;border-radius:11px;padding:14px 17px;background:#efad29;color:#111;font-weight:900;text-decoration:none}
.danger{width:100%;margin-top:12px;border:0;border-radius:10px;padding:12px;background:#8b2025;color:#fff;font-weight:800}
.net{padding:10px 14px;text-align:center;background:#7a1f1f;font-size:13px;font-weight:800}
.notice{border-color:#2f8f46}
</style></head><body>
<div class="net" id="net"></div>
<main><div class="brand">♧ BRECHÓ GETRES</div><a class="btn" href="/?menu=1">← VOLTAR</a>
<h1>Pedidos</h1><div id="lista"></div></main>
<script>
function get(k,d){try{return JSON.parse(localStorage.getItem(k)||JSON.stringify(d))}catch(e){return d}}
function set(k,v){localStorage.setItem(k,JSON.stringify(v))}
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function render(){
 const fila=get('getres_offline_sales',[]);
 let hist=get('getres_offline_history',[]);
 const acoes=get('getres_offline_actions',[]);
 const srv=get('getres_server_orders',[]);
 fila.forEach(p=>{if(!hist.some(x=>x.offline_id===p.offline_id))hist.unshift({...p,local_status:'PENDENTE'})});
 set('getres_offline_history',hist.slice(0,100));
 document.getElementById('net').textContent='OFFLINE • '+fila.length+' pedido(s) aguardando sincronização';

 const idsPend=new Set(fila.map(x=>x.offline_id));
 const offline=hist.filter(x=>idsPend.has(x.offline_id)||x.local_status==='PENDENTE');
 const avisos=acoes.map(a=>`<div class="box notice"><b>${a.tipo==='confirmar'?'✅ Pagamento confirmado offline':'❌ Cancelamento salvo offline'} • Venda #${a.vid}</b><div class="muted">Será sincronizado automaticamente quando a internet voltar.</div></div>`).join('');

 const offHtml=offline.map(p=>{
   const total=Number(p.total||0);
   return `<div class="box"><div class="row"><div><b>📴 Pedido offline</b><div class="muted">⏳ AGUARDANDO SINCRONIZAÇÃO</div><div class="muted">${esc(p.pagamento||'')}</div></div><div class="price">R$ ${total.toFixed(2).replace('.',',')}</div></div>
   <button class="danger" data-off="${esc(p.offline_id||'')}">🗑️ EXCLUIR PEDIDO OFFLINE</button></div>`;
 }).join('');

 const srvHtml=srv.map(v=>{
   const st=v.status||'AGUARDANDO_PAGAMENTO';
   const rotulo=st==='PAGO'?'✅ PAGO':st==='CANCELADO'?'❌ CANCELADO':'⏳ AGUARDANDO PAGAMENTO';
   return `<button class="box" style="width:100%;text-align:left" data-venda="${Number(v.id)}"><div class="row"><div><b>Venda #${Number(v.id)}</b><div class="muted">${rotulo}</div></div><div>R$ ${Number(v.total||0).toFixed(2)}</div></div></button>`;
 }).join('');

 document.getElementById('lista').innerHTML=avisos+offHtml+srvHtml || '<div class="box">Nenhum pedido salvo.</div>';
 document.querySelectorAll('[data-off]').forEach(b=>b.onclick=()=>{
   if(!confirm('Excluir este pedido offline antes da sincronização?'))return;
   const id=b.getAttribute('data-off');
   set('getres_offline_sales',get('getres_offline_sales',[]).filter(x=>x.offline_id!==id));
   set('getres_offline_history',get('getres_offline_history',[]).filter(x=>x.offline_id!==id));
   render();
 });
 document.querySelectorAll('[data-venda]').forEach(b=>b.onclick=()=>abrirVenda(Number(b.getAttribute('data-venda'))));
}
function abrirVenda(vid){
 const srv=get('getres_server_orders',[]);
 const v=srv.find(x=>Number(x.id)===Number(vid));
 if(!v){alert('Os dados desta venda ainda não estão salvos neste aparelho.');return}
 const st=v.status||'AGUARDANDO_PAGAMENTO';
 const rotulo=st==='PAGO'?'✅ PAGO':st==='CANCELADO'?'❌ CANCELADO':'⏳ AGUARDANDO PAGAMENTO';
 const pode=st!=='PAGO'&&st!=='CANCELADO';
 const total=Number(v.total||0).toFixed(2).replace('.',',');
 document.querySelector('main').innerHTML=`<div class="brand">♧ BRECHÓ GETRES</div>
 <button class="btn" id="voltaPedidos">← PEDIDOS</button><h1>Venda #${vid}</h1>
 <div class="box"><div class="price">R$ ${total}</div><div class="muted">Status: ${rotulo}</div>
 <div class="muted">Pagamento: ${esc(v.pagamento||'')}</div>
 <div class="muted">Recebimento: ${v.tipo_entrega==='entrega'?'Entrega':'Retirada no local'}</div></div>
 ${v.pagamento==='PIX'&&pode?'<div class="box" style="text-align:center"><b>💠 PIX QR CODE</b><div class="muted">O QR Code completo requer internet. O valor e a confirmação continuam disponíveis offline.</div></div>':''}
 ${pode?'<button class="btn" id="confirmaVenda">✅ CONFIRMAR PAGAMENTO OFFLINE</button><button class="danger" id="cancelaVenda">❌ CANCELAR PEDIDO OFFLINE</button>':''}
 ${st==='PAGO'?'<div class="box notice"><b>✅ PAGAMENTO CONFIRMADO</b></div>':''}`;
 document.getElementById('voltaPedidos').onclick=()=>location.reload();
 if(pode){
   document.getElementById('confirmaVenda').onclick=()=>filaAcao('confirmar',vid);
   document.getElementById('cancelaVenda').onclick=()=>filaAcao('cancelar',vid);
 }
}
function filaAcao(tipo,vid){
 const msg=tipo==='confirmar'?'Confirmar o pagamento desta venda?':'Cancelar esta venda?';
 if(!confirm(msg))return;
 let a=get('getres_offline_actions',[]);
 a=a.filter(x=>Number(x.vid)!==Number(vid));
 a.push({tipo:tipo,vid:Number(vid),criado_em:new Date().toISOString()});
 set('getres_offline_actions',a);
 let srv=get('getres_server_orders',[]);
 srv=srv.map(v=>Number(v.id)===Number(vid)?({...v,status:tipo==='confirmar'?'PAGO':'CANCELADO'}):v);
 set('getres_server_orders',srv);
 alert(tipo==='confirmar'?'Pagamento confirmado OFFLINE. Será sincronizado quando a internet voltar.':'Cancelamento salvo OFFLINE. Será sincronizado quando a internet voltar.');
 location.reload();
}
render();
</script></body></html>`;
}

function vendaOfflineHtml(vid){
  return `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Venda #${vid}</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#000;color:#fff;font-family:Arial,sans-serif}
main{width:min(100%,560px);margin:auto;padding:20px 18px 80px}.brand{text-align:center;color:#e7a92d;font-weight:900;font-size:25px;margin:16px 0 24px}
.box{border:1px solid #8a6422;border-radius:16px;padding:18px;margin:14px 0;background:#111}.muted{color:#bbb;margin-top:7px}
.price{color:#e7a92d;font-size:24px;font-weight:900}.btn,button{width:100%;border:0;border-radius:11px;padding:14px 17px;background:#efad29;color:#111;font-weight:900;text-decoration:none;display:block;text-align:center;margin-top:12px}
.danger{background:#8b2025;color:#fff}.net{padding:10px;text-align:center;background:#7a1f1f;font-size:13px;font-weight:800}
</style></head><body><div class="net">📴 Sem conexão</div><main>
<div class="brand">♧ BRECHÓ GETRES</div><a class="btn" href="/pedidos">← PEDIDOS</a>
<div id="conteudo"></div></main>
<script>
const vid=${vid};
function get(k,d){try{return JSON.parse(localStorage.getItem(k)||JSON.stringify(d))}catch(e){return d}}
function set(k,v){localStorage.setItem(k,JSON.stringify(v))}
const srv=get('getres_server_orders',[]);
const v=srv.find(x=>Number(x.id)===Number(vid));
if(!v){
 document.getElementById('conteudo').innerHTML='<div class="box"><b>Venda #'+vid+'</b><div class="muted">Os detalhes desta venda não estavam salvos neste aparelho.</div></div>';
}else{
 const st=v.status||'AGUARDANDO_PAGAMENTO';
 let botoes='';
 if(st!=='PAGO'&&st!=='CANCELADO'){
   botoes='<button id="confirmar">✅ CONFIRMAR PAGAMENTO OFFLINE</button><button class="danger" id="cancelar">❌ CANCELAR OFFLINE</button>';
 }
 document.getElementById('conteudo').innerHTML='<h1>Venda #'+vid+'</h1><div class="box"><div class="price">R$ '+Number(v.total||0).toFixed(2).replace('.',',')+'</div><div class="muted">Status: '+st+'</div><div class="muted">Pagamento: '+(v.pagamento||'')+'</div></div>'+botoes;
 const q=(tipo)=>{let a=get('getres_offline_actions',[]);if(!a.some(x=>x.tipo===tipo&&Number(x.vid)===vid))a.push({tipo:tipo,vid:vid,criado_em:new Date().toISOString()});set('getres_offline_actions',a);location='/pedidos'};
 const bc=document.getElementById('confirmar');if(bc)bc.onclick=()=>{if(confirm('Confirmar o pagamento desta venda?'))q('confirmar')};
 const bx=document.getElementById('cancelar');if(bx)bx.onclick=()=>{if(confirm('Cancelar esta venda?'))q('cancelar')};
}
</script></body></html>`;
}

self.addEventListener('fetch',e=>{
  const req=e.request;
  if(req.method!=='GET') return;
  const url=new URL(req.url);
  if(url.origin!==self.location.origin) return;

  if(req.mode==='navigate'){
    e.respondWith((async()=>{
      const c=await caches.open(CACHE);
      const key=(['/destaques','/produtos','/carrinho','/pedidos'].includes(url.pathname))
        ? url.pathname : (url.pathname==='/'?'/?menu=1':url.pathname+(url.search||''));

      try{
        const r=await fetch(req,{cache:'no-store'});
        if(r && r.ok) await c.put(key,r.clone());
        return r;
      }catch(_){
        if(url.pathname==='/pedidos'){
          return new Response(pedidosOfflineHtml(),{status:200,headers:{'Content-Type':'text/html; charset=utf-8'}});
        }
        const mv=url.pathname.match(/^\/venda\/(\d+)$/);
        if(mv){
          return new Response(vendaOfflineHtml(Number(mv[1])),{status:200,headers:{'Content-Type':'text/html; charset=utf-8'}});
        }
        const hit=await c.match(key);
        if(hit) return hit;
        return new Response(
          '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><body style="background:#000;color:#fff;font-family:Arial;padding:24px"><h2>Sem conexão</h2><p>Esta tela ainda não está disponível offline neste aparelho.</p><button onclick="history.back()" style="padding:14px">VOLTAR</button></body>',
          {status:503,headers:{'Content-Type':'text/html; charset=utf-8'}}
        );
      }
    })());
    return;
  }

  if(url.pathname.startsWith('/produto-foto/') || url.pathname.startsWith('/foto-arquivo/')){
    e.respondWith((async()=>{
      const c=await caches.open(CACHE);
      try{
        const r=await fetch(req,{cache:'no-store'});
        if(r.ok) await c.put(req,r.clone());
        return r;
      }catch(_){
        const hit=await c.match(req);
        return hit || Response.error();
      }
    })());
  }
});
"""
    resp=Response(js,mimetype="application/javascript")
    resp.headers["Cache-Control"]="no-store, no-cache, must-revalidate, max-age=0"
    return resp

init()
migrar_nome_getres()
if __name__=="__main__":
    print("BRECHÓ GETRES: http://127.0.0.1:5000")
    app.run(host="0.0.0.0",port=5000,debug=False)

