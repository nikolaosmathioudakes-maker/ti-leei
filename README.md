# ΤΙ ΛΕΕΙ; — Production News App

Αυτή είναι κανονική Flask εφαρμογή με backend και SQLite, όχι στατικό demo.

## Περιλαμβάνει
- 40 configured news sources
- πραγματικό RSS/Atom ingestion
- Ελλάδα / Κρήτη / Χανιά / Κόσμος / Οικονομία / Τεχνολογία / Επίσημες
- database αποθήκευση
- πραγματικές σελίδες άρθρων `/article/<id>`
- link προς την αρχική πηγή
- αναζήτηση και φίλτρα
- refresh endpoint
- AI verification endpoint
- responsive mobile UI
- προαιρετικό OpenAI Responses API

## Εγκατάσταση
Python 3.11+
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# ή cp .env.example .env
python app.py
```
Άνοιξε: http://127.0.0.1:5000

## AI
Βάλε το API key μόνο στο `.env`:
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-6-luna

Χωρίς key, η εφαρμογή λειτουργεί κανονικά ως news aggregator αλλά το AI verification απενεργοποιείται.

## Σημαντικό για production
- Έλεγξε τους όρους χρήσης/licensing κάθε publisher πριν από εμπορική χρήση.
- Η εφαρμογή αποθηκεύει τίτλο, περίληψη και link από RSS· δεν αντιγράφει ολόκληρα άρθρα.
- Τα Google News feeds για Reuters/AP είναι discovery/syndication feeds και όχι επίσημα Reuters/AP RSS. Αυτό είναι σημαντικό για attribution και verification.
- Για πραγματικό publishing pipeline χρειάζεται admin approval πριν από αυτόματο δημοσίευμα.
- Προτείνεται PostgreSQL + Redis/Celery/cron όταν ανέβει σε production.
