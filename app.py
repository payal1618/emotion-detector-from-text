# app.py
from flask import Flask, render_template, request, jsonify, send_file
from lexicons import EMOTION_KEYWORDS
import re
import io
from datetime import datetime

app = Flask(__name__, static_folder='static', template_folder='templates')

# helper - split into sentences (simple)
SENT_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

def tokenize_words(text):
    # lowercase, remove non-alpha except apostrophe
    words = re.findall(r"[A-Za-z']+", text.lower())
    return words

def analyze_sentence(sentence):
    words = tokenize_words(sentence)
    counts = {emo: 0 for emo in EMOTION_KEYWORDS}
    for w in words:
        for emo, kws in EMOTION_KEYWORDS.items():
            # partial match allowed (stem-like) for small vocab
            if w in kws:
                counts[emo] += 1
            else:
                # quick partial match to catch "excited" vs "excite"
                for kw in kws:
                    if kw in w or w in kw:
                        counts[emo] += 1
                        break
    total = sum(counts.values())
    # produce normalized scores 0..1
    if total == 0:
        # fallback: neutral small score
        return {"scores": {e: 0.0 for e in counts}, "top": "neutral", "raw": counts}
    scores = {e: (counts[e] / total) for e in counts}
    top = max(scores.items(), key=lambda x: x[1])[0]
    return {"scores": scores, "top": top, "raw": counts}

def aggregate_results(sentence_analyses):
    # sum up per-emotion scores and normalize to percentages
    agg = {e: 0.0 for e in EMOTION_KEYWORDS}
    for s in sentence_analyses:
        for e, sc in s["scores"].items():
            agg[e] += sc
    # normalize by number of sentences then convert to percent
    n = max(1, len(sentence_analyses))
    for e in agg:
        agg[e] = round((agg[e] / n) * 100, 2)
    return agg

def auto_reply(aggregate):
    # simple rules: highest emotion -> formulate reply
    primary = max(aggregate.items(), key=lambda x: x[1])
    emo, score = primary
    if score < 15:
        return "Thanks for sharing — tell me more if you'd like."
    if emo == "happy":
        return "Sounds exciting! Keep smiling 😊"
    if emo == "sad":
        return "I'm sorry you're feeling down. If you want to talk, I'm here."
    if emo == "angry":
        return "I can see you're upset. Try some deep breaths or a short walk."
    if emo == "nervous":
        return "If you're nervous, try slow deep breaths — it helps. You've got this!"
    if emo == "grateful":
        return "That's wonderful — gratitude is powerful!"
    if emo == "surprised":
        return "Wow — that sounds surprising!"
    return "Thanks for sharing."

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/detect', methods=['POST'])
def detect():
    data = request.json or {}
    text = data.get('text', '')[:20000]  # limit
    # split into sentences
    raw_sentences = [s.strip() for s in SENT_SPLIT_RE.split(text) if s.strip()]
    if not raw_sentences:
        raw_sentences = [text.strip()] if text.strip() else []
    sentence_results = []
    for sent in raw_sentences:
        res = analyze_sentence(sent)
        sentence_results.append({
            "sentence": sent,
            "top": res["top"],
            "scores": {k: round(v, 3) for k, v in res["scores"].items()},
            "raw_counts": res["raw"]
        })
    aggregate = aggregate_results([{"scores": r["scores"]} for r in sentence_results]) if sentence_results else {e:0 for e in EMOTION_KEYWORDS}
    reply = auto_reply(aggregate)
    response = {
        "sentences": sentence_results,
        "aggregate": aggregate,
        "auto_reply": reply,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    return jsonify(response)

@app.route('/api/export', methods=['POST'])
def export():
    payload = request.json or {}
    text = payload.get("text", "")
    result = payload.get("result", {})
    # prepare simple text summary
    buf = io.StringIO()
    buf.write("Emotion Detector - Summary\n")
    buf.write(f"Timestamp: {datetime.utcnow().isoformat()}Z\n\n")
    buf.write("Input Text:\n")
    buf.write(text + "\n\n")
    buf.write("Aggregate Emotions (%):\n")
    agg = result.get("aggregate", {})
    for k, v in agg.items():
        buf.write(f"- {k}: {v}%\n")
    buf.write("\nSentence-wise:\n")
    for s in result.get("sentences", []):
        buf.write(f"> {s.get('sentence')}\n")
        tops = s.get('scores', {})
        # show top 3 scores
        sorted_scores = sorted(tops.items(), key=lambda x: x[1], reverse=True)[:3]
        buf.write("  " + ", ".join([f"{e}: {round(sc,3)}" for e, sc in sorted_scores]) + "\n")
    buf.write("\nAuto-reply:\n")
    buf.write(result.get("auto_reply","") + "\n")
    # return as downloadable txt
    mem = io.BytesIO()
    mem.write(buf.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, mimetype='text/plain', as_attachment=True, attachment_filename='emotion_summary.txt')

if __name__ == '__main__':
    app.run(debug=True)
