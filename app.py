import os, re, hashlib, sqlite3, html as htmlmod
from datetime import datetime, timezone
from urllib.parse import urlparse
import feedparser
from flask import Flask, render_template, request, redirect, url_for, jsonify
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

app = Flask(__name__)
DB="news.db"
MAX_PER_SOURCE=int(os.getenv("MAX_PER_SOURCE","20"))
SOURCES = [('ERT News', 'Ελλάδα', 'https://www.ertnews.gr/feed/'), ('SKAI', 'Ελλάδα', 'https://www.skai.gr/rss'), ('in.gr', 'Ελλάδα', 'https://www.in.gr/feed/'), ('News.gr', 'Ελλάδα', 'http://www.news.gr/rss.ashx'), ('Naftemporiki', 'Οικονομία', 'https://www.naftemporiki.gr/rss/'), ('News247', 'Ελλάδα', 'https://www.news247.gr/feed/'), ('Proto Thema', 'Ελλάδα', 'https://www.protothema.gr/rss/'), ('Kathimerini', 'Ελλάδα', 'https://www.kathimerini.gr/feed/'), ('Newsit', 'Ελλάδα', 'https://www.newsit.gr/feed/'), ('CNN Greece', 'Ελλάδα', 'https://www.cnn.gr/rss'), ('Newsbomb', 'Ελλάδα', 'https://www.newsbomb.gr/feed'), ('Zougla', 'Ελλάδα', 'https://www.zougla.gr/feed'), ('Ethnos', 'Ελλάδα', 'https://www.ethnos.gr/rss'), ('Eleftherostypos', 'Ελλάδα', 'https://www.eleftherostypos.gr/feed/'), ('EFSYN', 'Ελλάδα', 'https://www.efsyn.gr/rss.xml'), ('Zarpanews', 'Χανιά', 'https://news.google.com/rss/search?q=site%3Azarpanews.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'), ('Flashnews', 'Κρήτη', 'https://news.google.com/rss/search?q=site%3Aflashnews.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'), ('Neakriti', 'Κρήτη', 'https://news.google.com/rss/search?q=site%3Aneakriti.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'), ('Hania News', 'Χανιά', 'https://news.google.com/rss/search?q=site%3Ahania.news+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'), ('Creta24', 'Κρήτη', 'https://news.google.com/rss/search?q=site%3Acreta24.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'), ('Ekriti', 'Κρήτη', 'https://news.google.com/rss/search?q=site%3Aekriti.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'), ('BBC News', 'Κόσμος', 'https://feeds.bbci.co.uk/news/rss.xml'), ('BBC World', 'Κόσμος', 'https://feeds.bbci.co.uk/news/world/rss.xml'), ('DW', 'Κόσμος', 'https://rss.dw.com/rdf/rss-en-all'), ('France24', 'Κόσμος', 'https://www.france24.com/en/rss'), ('The Guardian', 'Κόσμος', 'https://www.theguardian.com/world/rss'), ('Google Reuters', 'Κόσμος', 'https://news.google.com/rss/search?q=site%3Areuters.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'), ('Google AP', 'Κόσμος', 'https://news.google.com/rss/search?q=site%3Aapnews.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'), ('Google Bloomberg', 'Οικονομία', 'https://news.google.com/rss/search?q=site%3Abloomberg.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'), ('Google CNBC', 'Οικονομία', 'https://news.google.com/rss/search?q=site%3Acnbc.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'), ('Google FT', 'Οικονομία', 'https://news.google.com/rss/search?q=site%3Aft.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'), ('TechCrunch', 'Τεχνολογία', 'https://techcrunch.com/feed/'), ('The Verge', 'Τεχνολογία', 'https://www.theverge.com/rss/index.xml'), ('Ars Technica', 'Τεχνολογία', 'https://feeds.arstechnica.com/arstechnica/index'), ('Google Wired', 'Τεχνολογία', 'https://news.google.com/rss/search?q=site%3Awired.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'), ('Greek Police', 'Επίσημες', 'https://www.astynomia.gr/feed/'), ('Civil Protection', 'Επίσημες', 'https://civilprotection.gov.gr/rss'), ('Ministry Agriculture', 'Επίσημες', 'https://www.minagric.gov.gr/rss-press-release'), ('Government', 'Επίσημες', 'https://www.primeminister.gr/feed'), ('European Commission', 'Επίσημες', 'https://ec.europa.eu/commission/presscorner/api/rss')]

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS articles(
      id INTEGER PRIMARY KEY, source TEXT, category TEXT, title TEXT, summary TEXT,
      url TEXT UNIQUE, published TEXT, fetched TEXT, cluster TEXT, ai_json TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS saved(
      id INTEGER PRIMARY KEY, article_id INTEGER UNIQUE, created TEXT)""")
    c.commit(); c.close()

def clean(s):
    return re.sub(r"\s+"," ", re.sub("<[^>]+>"," ", s or "")).strip()

def feed_source(source,category,feedurl):
    try:
        f=feedparser.parse(feedurl)
        out=[]
        for e in f.entries[:MAX_PER_SOURCE]:
            title=clean(getattr(e,"title",""))
            link=getattr(e,"link","")
            if not title or not link: continue
            summary=clean(getattr(e,"summary",getattr(e,"description","")))
            pub=getattr(e,"published","") or getattr(e,"updated","")
            out.append((source,category,title,summary,link,pub))
        return out
    except Exception:
        return []

def key(title):
    words=re.findall(r"[A-Za-zΑ-Ωα-ω0-9]{4,}",title.lower())
    stop={"στην","στη","στο","στης","τους","μετά","για","από","και","the","with","that","this","from","news","said","έχει","όπως"}
    return set(w for w in words if w not in stop)

def cluster_articles(rows):
    clusters=[]
    for row in rows:
        s=key(row[2]); best=None; score=0
        for cl in clusters:
            common=len(s & cl["words"]); denom=max(1,min(len(s),len(cl["words"])))
            sim=common/denom
            if sim>score: score=sim; best=cl
        if best and score>=0.38:
            best["items"].append(row); best["words"] |= s
        else:
            clusters.append({"words":set(s),"items":[row]})
    return clusters

def refresh():
    rows=[]
    for s,c,u in SOURCES: rows += feed_source(s,c,u)
    # de-duplicate by URL
    seen=set(); cleanrows=[]
    con=db()
    for r in rows:
        if r[4] in seen: continue
        seen.add(r[4])
        try:
            con.execute("""INSERT OR IGNORE INTO articles(source,category,title,summary,url,published,fetched)
              VALUES(?,?,?,?,?,?,?)""",(*r,datetime.now(timezone.utc).isoformat()))
        except Exception: pass
        cleanrows.append(r)
    con.commit(); con.close()
    return len(cleanrows)

def articles(limit=120, category=None, q=None):
    c=db()
    sql="SELECT * FROM articles"; params=[]; where=[]
    if category and category!="Όλα": where.append("category=?"); params.append(category)
    if q: where.append("(title LIKE ? OR summary LIKE ?)"); params += [f"%{q}%",f"%{q}%"]
    if where: sql+=" WHERE "+" AND ".join(where)
    sql+=" ORDER BY id DESC LIMIT ?"; params.append(limit)
    rows=c.execute(sql,params).fetchall(); c.close(); return rows

def ai_verify(items):
    if not OpenAI or not os.getenv("OPENAI_API_KEY"): return None
    client=OpenAI()
    payload=[{"source":x["source"],"title":x["title"],"summary":x["summary"],"url":x["url"]} for x in items[:12]]
    schema={"type":"object","properties":{
      "status":{"type":"string","enum":["confirmed","developing","unconfirmed","disputed"]},
      "headline":{"type":"string"},"summary":{"type":"string"},
      "claims":{"type":"array","items":{"type":"object","properties":{
        "claim":{"type":"string"},"supporting_sources":{"type":"array","items":{"type":"string"}},
        "contradicting_sources":{"type":"array","items":{"type":"string"}},
        "confidence":{"type":"number"}
      },"required":["claim","supporting_sources","contradicting_sources","confidence"],"additionalProperties":False}},
      "missing_verification":{"type":"array","items":{"type":"string"}}
    },"required":["status","headline","summary","claims","missing_verification"],"additionalProperties":False}
    prompt=("Analyze these reports as a newsroom verification editor. Do not assume repetition is independent confirmation. "
            "Separate primary/official evidence from secondary reporting. Do not invent facts. Return only the requested JSON.\n"+
            str(payload))
    r=client.responses.create(model=os.getenv("OPENAI_MODEL","gpt-6-luna"),
      input=prompt, text={"format":{"type":"json_schema","name":"verification","schema":schema,"strict":True}})
    return r.output_text

@app.route("/")
def home():
    if not db().execute("SELECT 1 FROM articles LIMIT 1").fetchone(): refresh()
    cat=request.args.get("cat","Όλα"); q=request.args.get("q","")
    rows=articles(120,cat,q)
    return render_template("index.html", rows=rows, sources=SOURCES, cat=cat, q=q, saved_ids=saved_ids())

@app.route("/article/<int:aid>")
def article(aid):
    c=db(); row=c.execute("SELECT * FROM articles WHERE id=?",(aid,)).fetchone(); c.close()
    if not row: return "Not found",404
    # Related articles by category
    related=articles(12,row["category"])
    return render_template("article.html",a=row,related=related)

@app.post("/refresh")
def refresh_route():
    n=refresh(); return redirect(url_for("home"))

@app.post("/api/verify/<int:aid>")
def verify(aid):
    c=db(); rows=c.execute("SELECT * FROM articles WHERE id=?",(aid,)).fetchall()
    if not rows: return jsonify({"error":"not found"}),404
    base=rows[0]; allrows=c.execute("SELECT * FROM articles WHERE category=? ORDER BY id DESC LIMIT 50",(base["category"],)).fetchall(); c.close()
    # Lightweight same-title cluster around the selected story
    words=key(base["title"]); candidates=[x for x in allrows if len(words & key(x["title"]))>=2][:12]
    result=ai_verify(candidates)
    if result:
        c=db(); c.execute("UPDATE articles SET ai_json=? WHERE id=?",(result,aid)); c.commit(); c.close()
        return jsonify({"ok":True,"analysis":result})
    return jsonify({"ok":False,"message":"OPENAI_API_KEY not configured; live AI verification is disabled."})

@app.post("/save/<int:aid>")
def save(aid):
    c=db()
    try: c.execute("INSERT OR IGNORE INTO saved(article_id,created) VALUES(?,?)",(aid,datetime.now(timezone.utc).isoformat())); c.commit()
    finally: c.close()
    return redirect(request.referrer or url_for("home"))

@app.post("/unsave/<int:aid>")
def unsave(aid):
    c=db(); c.execute("DELETE FROM saved WHERE article_id=?",(aid,)); c.commit(); c.close()
    return redirect(request.referrer or url_for("home"))

def saved_ids():
    c=db(); ids={r["article_id"] for r in c.execute("SELECT article_id FROM saved")}; c.close(); return ids

@app.route("/health")
def health(): return jsonify({"ok":True,"sources":len(SOURCES),"articles":len(articles(10000))})

init()
if __name__=="__main__":
    app.run(host=os.getenv("HOST","0.0.0.0"),port=int(os.getenv("PORT","5000")),debug=os.getenv("DEBUG","0")=="1")
