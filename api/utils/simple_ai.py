from typing import List, Dict
MODEL = "simple-ai-v0"

def analyze_doc(content: bytes, lang: str = "bi") -> Dict:
    text = content.decode(errors='ignore')
    req_tech: List[Dict] = []
    if text:
        req_tech.append({"item":"Router CCR2004","qty":2,"specs":"...","notes":"..."})
        req_tech.append({"item":"Switch 24 PoE","qty":3,"specs":"...","notes":"..."})
    req_fin = [{ "item": r["item"], "unit":"pcs","qty":r["qty"],"est_price":0,"currency":"USD"} for r in req_tech]
    return {
        "model": MODEL,
        "summary_ar": "ملخص مبدئي للمناقصة: متطلبات فنية/مالية تقريبية — راجع وعدّل قبل التوليد.",
        "summary_en": "Preliminary tender summary: rough technical/financial requirements — review before final generation.",
        "requirements_tech": req_tech,
        "requirements_fin": req_fin,
        "questions": ["ما مدة التسليم؟","هل الزيارة إلزامية؟","ما العملة المعتمدة؟"]
    }
