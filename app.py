import os, re, sqlite3, html
from datetime import datetime, timezone
import feedparser
from flask import Flask, render_template, request, redirect, url_for, jsonify

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

app = Flask(__name__)
DB = "news.db"
MAX_PER_SOURCE = int(os.getenv("MAX_PER_SOURCE", "20"))

SOURCES = [
    ('ERT News', 'Ελλάδα', 'https://www.ertnews.gr/feed/'),
    ('SKAI', 'Ελλάδα', 'https://www.skai.gr/rss'),
    ('in.gr', 'Ελλάδα', 'https://www.in.gr/feed/'),
    ('News.gr', 'Ελλάδα', 'http://www.news.gr/rss.ashx'),
    ('Naftemporiki', 'Οικονομία', 'https://www.naftemporiki.gr/rss/'),
    ('News247', 'Ελλάδα', 'https://www.news247.gr/feed/'),
    ('Proto Thema', 'Ελλάδα', 'https://www.protothema.gr/rss/'),
    ('Kathimerini', 'Ελλάδα', 'https://www.kathimerini.gr/feed/'),
    ('Newsit', 'Ελλάδα', 'https://www.newsit.gr/feed/'),
    ('CNN Greece', 'Ελλάδα', 'https://www.cnn.gr/rss'),
    ('Newsbomb', 'Ελλάδα', 'https://www.newsbomb.gr/feed'),
    ('Zougla', 'Ελλάδα', 'https://www.zougla.gr/feed'),
    ('Ethnos', 'Ελλάδα', 'https://www.ethnos.gr/rss'),
    ('Eleftherostypos', 'Ελλάδα', 'https://www.eleftherostypos.gr/feed/'),
    ('EFSYN', 'Ελλάδα', 'https://www.efsyn.gr/rss.xml'),
    ('Zarpanews', 'Χανιά', 'https://news.google.com/rss/search?q=site%3Azarpanews.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'),
    ('Flashnews', 'Κρήτη', 'https://news.google.com/rss/search?q=site%3Aflashnews.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'),
    ('Neakriti', 'Κρήτη', 'https://news.google.com/rss/search?q=site%3Aneakriti.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'),
    ('Hania News', 'Χανιά', 'https://news.google.com/rss/search?q=site%3Ahania.news+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'),
    ('Creta24', 'Κρήτη', 'https://news.google.com/rss/search?q=site%3Acreta24.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'),
    ('Ekriti', 'Κρήτη', 'https://news.google.com/rss/search?q=site%3Aekriti.gr+when%3A24h&hl=el&gl=GR&ceid=GR%3Ael'),
    ('BBC News', 'Κόσμος', 'https://feeds.bbci.co.uk/news/rss.xml'),
    ('BBC World', 'Κόσμος', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
    ('DW', 'Κόσμος', 'https://rss.dw.com/rdf/rss-en-all'),
    ('France24', 'Κόσμος', 'https://www.france24.com/en/rss'),
    ('The Guardian', 'Κόσμος', 'https://www.theguardian.com/world/rss'),
    ('Google Reuters', 'Κόσμος', 'https://news.google.com/rss/search?q=site%3Areuters.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'),
    ('Google AP', 'Κόσμος', 'https://news.google.com/rss/search?q=site%3Aapnews.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'),
    ('Google Bloomberg', 'Οικονομία', 'https://news.google.com/rss/search?q=site%3Abloomberg.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'),
    ('Google CNBC', 'Οικονομία', 'https://news.google.com/rss/search?q=site%3Acnbc.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'),
    ('Google FT', 'Οικονομία', 'https://news.google.com/rss/search?q=site%3Aft.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'),
    ('TechCrunch', 'Τεχνολογία', 'https://techcrunch.com/feed/'),
    ('The Verge', 'Τεχνολογία', 'https://www.theverge.com/rss/index.xml'),
    ('Ars Technica', 'Τεχνολογία', 'https://feeds.arstechnica.com/arstechnica/index'),
    ('Google Wired', 'Τεχνολογία', 'https://news.google.com/rss/search?q=site%3Awired.com+when%3A24h&hl=en-US&gl=US&ceid=US%3Aen'),
    ('Greek Police', 'Επίσημες', 'https://www.astynomia.gr/feed/'),
    ('Civil Protection', 'Επίσημες', 'https://civilprotection.gov.gr/rss'),
    ('Ministry Agriculture', 'Επίσημες', 'https://www.minagric.gov.gr/rss-press-release'),
    ('Government', 'Επίσημες', 'https://www.primeminister.gr/feed'),
    ('European Commission', 'Επίσημες', 'https://ec.europa.eu/commission/presscorner/api/rss')
]

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = db()
    c.execute("""CREATE TABLE IF NOT EXISTS articles(
        id INTEGER PRIMARY KEY, source TEXT, category TEXT, title TEXT,
        summary TEXT, url TEXT UNIQUE, published TEXT, fetched TEXT,
        cluster TEXT, ai_json TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS saved(
        id INTEGER PRIMARY KEY, article_id INTEGER UNIQUE, created TEXT)""")
    c.commit()
    c.close()

def clean(s):
    # Decode HTML entities such as &nbsp; and strip tags from feed content.
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = s.replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()

def feed_source(source, category, feedurl):
    try:
        f = feedparser.parse(feedurl)
        out = []
        for e in f.entries[:MAX_PER_SOURCE]:
            title = clean(getattr(e, "title", ""))
            link = getattr(e, "link", "")
            if not title or not link:
                continue
            summary = clean(getattr(e, "summary", getattr(e, "description", "")))
            pub = getattr(e, "published", "") or getattr(e, "updated", "")
            out.append((source, category, title, summary, link, pub))
        return out
    except Exception:
        return []

def key(title):
    words = re.findall(r"[A-Za-zΑ-Ωα-ω0-9]{3,}", (title or "").lower())
    stop = {"στην","στη","στο","στης","τους","μετά","για","από","και",
            "the","with","that","this","from","news","said","έχει","όπως",
            "που","των","της","τον","την","ένα","μια","ένα"}
    return set(w for w in words if w not in stop)

def refresh():
    rows = []
    for s, c, u in SOURCES:
        rows += feed_source(s, c, u)
    seen = set()
    con = db()
    for r in rows:
        if r[4] in seen:
            continue
        seen.add(r[4])
        try:
            con.execute("""INSERT OR IGNORE INTO articles
                (source,category,title,summary,url,published,fetched)
                VALUES(?,?,?,?,?,?,?)""",
                (*r, datetime.now(timezone.utc).isoformat()))
        except Exception:
            pass
    con.commit()
    con.close()
    return len(seen)

CRETE_TERMS = {
    "κρήτη","κρητη","κρητών","κρητων","κρητικός","κρητικος",
    "χανιά","χανια","χανίων","χανιων","ηράκλειο","ηρακλειο",
    "ηρακλείου","ηρακλειου","ρεθύμν","ρεθυμν","ρεθύμνης","ρεθυμνης",
    "λασίθ","λασιθ","λασιθίου","λασιθιου","άγιος νικόλαος","αγιος νικολαος",
    "σιτεία","σιτεια","ιεράπετρα","ιεραπετρα","μαλεβίζι","μαλεβιζι",
    "αποκόρωνας","αποκορωνας","πλατανιάς","πλατανιας","κίσσαμος","κισσαμος",
    "φαλάσαρνα","φαλασαρνα","σούδα","σουδα","ακρωτήρι","ακρωτηρι",
    "μοίρες","μοιρες","τυμπάκι","τυμπακι","γάζι","γαζι"
}
CHANIA_TERMS = {
    "χανιά","χανια","χανίων","χανιων","σούδα","σουδα",
    "ακρωτήρι","ακρωτηρι","αποκόρωνας","αποκορωνας",
    "πλατανιάς","πλατανιας","κίσσαμος","kισσαμος",
    "φαλάσαρνα","φαλασαρνα"
}

def topical_match(row, category):
    text = (row["title"] + " " + row["summary"]).lower()
    terms = CRETE_TERMS if category == "Κρήτη" else CHANIA_TERMS
    return any(term in text for term in terms)

def articles(limit=120, category=None, q=None):
    c = db()
    sql = "SELECT * FROM articles"
    params, where = [], []
    if category and category != "Όλα":
        where.append("category=?")
        params.append(category)
    if q:
        where.append("(title LIKE ? OR summary LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if where:
        sql += " WHERE " + " AND ".join(where)
    # Fetch a larger pool before topical filtering, otherwise unrelated stories
    # can push relevant Crete/Chania stories out of the first 120 results.
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(limit * 8, limit) if category in ("Κρήτη", "Χανιά") else limit)
    rows = c.execute(sql, params).fetchall()
    c.close()
    if category in ("Κρήτη", "Χανιά"):
        rows = [row for row in rows if topical_match(row, category)]
    return rows[:limit]

def title_groups(rows):
    """Greedy title-similarity clusters; source count is shown, not treated as truth score."""
    groups = []
    for row in rows:
        words = key(row["title"])
        best, best_score = None, 0.0
        if words:
            for group in groups:
                # Avoid merging different categories except when viewing all news.
                gw = group["words"]
                score = len(words & gw) / max(1, min(len(words), len(gw)))
                if score > best_score:
                    best, best_score = group, score
        if best is not None and best_score >= 0.55 and row["source"] not in {x["source"] for x in best["items"]}:
            best["items"].append(row)
            best["words"] |= words
        else:
            groups.append({"items":[row], "words":set(words)})
    result = []
    for g in groups:
        items = sorted(g["items"], key=lambda x: x["id"], reverse=True)
        result.append({"lead":items[0], "items":items, "source_count":len({x["source"] for x in items})})
    return result

def ai_verify(items):
    if not OpenAI or not os.getenv("OPENAI_API_KEY"):
        return None
    client = OpenAI()
    payload = [{"source":x["source"],"title":x["title"],"summary":x["summary"],"url":x["url"]} for x in items[:12]]
    prompt = ("Analyze these reports as a newsroom verification editor. Do not assume repetition is independent confirmation. "
              "Separate primary/official evidence from secondary reporting. Do not invent facts. Return only the requested JSON.\n" + str(payload))
    schema = {
        "type":"object",
        "properties":{
            "status":{"type":"string","enum":["confirmed","developing","unconfirmed","disputed"]},
            "headline":{"type":"string"},
            "summary":{"type":"string"},
            "claims":{"type":"array","items":{"type":"object","properties":{
                "claim":{"type":"string"},
                "supporting_sources":{"type":"array","items":{"type":"string"}},
                "contradicting_sources":{"type":"array","items":{"type":"string"}},
                "confidence":{"type":"number"}
            },"required":["claim","supporting_sources","contradicting_sources","confidence"],"additionalProperties":False}},
            "missing_verification":{"type":"array","items":{"type":"string"}}
        },
        "required":["status","headline","summary","claims","missing_verification"],
        "additionalProperties":False
    }
    r = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
        input=prompt,
        text={"format":{"type":"json_schema","name":"verification","schema":schema,"strict":True}}
    )
    return r.output_text

@app.route("/")
def home():
    c = db()
    has_articles = c.execute("SELECT 1 FROM articles LIMIT 1").fetchone()
    c.close()
    if not has_articles:
        refresh()
    cat = request.args.get("cat", "Όλα")
    q = request.args.get("q", "")
    rows = articles(120, cat, q)
    groups = title_groups(rows)
    return render_template("index.html", groups=groups, rows=rows, sources=SOURCES,
                           cat=cat, q=q, saved_ids=saved_ids())

@app.route("/article/<int:aid>")
def article(aid):
    c = db()
    row = c.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
    c.close()
    if not row:
        return "Not found", 404
    related = articles(12, row["category"])
    return render_template("article.html", a=row, related=related)

@app.post("/refresh")
def refresh_route():
    refresh()
    return redirect(url_for("home", cat=request.args.get("cat", "Όλα")))

@app.post("/api/verify/<int:aid>")
def verify(aid):
    c = db()
    base = c.execute("SELECT * FROM articles WHERE id=?", (aid,)).fetchone()
    if not base:
        c.close()
        return jsonify({"error":"not found"}), 404
    allrows = c.execute("SELECT * FROM articles ORDER BY id DESC LIMIT 200").fetchall()
    c.close()
    words = key(base["title"])
    candidates = [x for x in allrows if len(words & key(x["title"])) >= 2][:12]
    result = ai_verify(candidates)
    if result:
        c = db()
        c.execute("UPDATE articles SET ai_json=? WHERE id=?", (result, aid))
        c.commit()
        c.close()
        return jsonify({"ok":True, "analysis":result})
    return jsonify({"ok":False, "message":"OPENAI_API_KEY not configured; live AI verification is disabled."})

@app.post("/save/<int:aid>")
def save(aid):
    c = db()
    try:
        c.execute("INSERT OR IGNORE INTO saved(article_id,created) VALUES(?,?)",
                  (aid, datetime.now(timezone.utc).isoformat()))
        c.commit()
    finally:
        c.close()
    return redirect(request.referrer or url_for("home"))

@app.post("/unsave/<int:aid>")
def unsave(aid):
    c = db()
    c.execute("DELETE FROM saved WHERE article_id=?", (aid,))
    c.commit()
    c.close()
    return redirect(request.referrer or url_for("home"))

def saved_ids():
    c = db()
    ids = {r["article_id"] for r in c.execute("SELECT article_id FROM saved")}
    c.close()
    return ids

@app.route("/health")
def health():
    return jsonify({"ok":True, "sources":len(SOURCES), "articles":len(articles(10000))})

init()
if __name__ == "__main__":
    app.run(host=os.getenv("HOST","0.0.0.0"),
            port=int(os.getenv("PORT","5000")),
            debug=os.getenv("DEBUG","0")=="1")
