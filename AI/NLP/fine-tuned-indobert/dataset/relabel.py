import csv
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "processed" / "comments_labeled.csv"
OUT = ROOT / "data" / "dataset" / "relabel_draft.csv"

COLORS = [
    "hitam", "item", "putih", "pth", "cream", "krem", "navy", "sage", "mocca", "moka",
    "coklat", "cokelat", "abu", "beige", "maroon", "army", "kuning", "biru", "merah",
    "hijau", "ungu", "pink", "grey", "gray", "tosca", "salem", "peach", "brown", "warna",
    "charcoal", "carcoal", "choco", "coffee",
]
SIZES = ["xs", "s", "m", "l", "xl", "xxl", "xxxl", "free", "all size"]
SIZE_RE = re.compile(
    r"\b(size|sz|ukuran|uk|chart|zize|s|m|l|xl|xxl|xxxl|xs|all\s*size|free|ld|lp|lb|lingkar)\b",
    re.IGNORECASE,
)
BODY_RE = re.compile(
    r"\b(bb|tb|ld|lp|lb)\s*\d+(\s*an)?\b|\bbb\d+(an)?\b|\btb\d+(an)?\b|\bld\d+\b|\blp\d+\b|\blb\d+\b"
    r"|\b(kg|cm)\b|berat|tinggi\s+(badan|\d)|lingkar|badan\b|umur|usia"
    r"|^\s*\d{1,3}\s+\d{2,3}\s*\??$"
    r"|\b(?:1\d{2}|2\d{2})\s*,\s*\d{2,3}(?:cm|kg)?\b|\b\d{2,3}\s*,\s*(?:1\d{2}|2\d{2})(?:cm|kg)?\b"
    r"|\b\d{2,3}(?:cm|kg)\b|\b\d{2,3}\s+\d{1,3}\s+(size|sz|uk|ukuran)\b|\b\d{3}\s+(s/m|m/l|s\b|m\b|l\b)\b"
    r"|\b\d{2,3}\s+\d{3}\b|\b\d{2,3}\s*[-–]\s*\d{2,3}\b|\b\d{2,3}\s+\d{2,3}\b$|\b\d{2,3}\s+\d{2,3}\b",
    re.IGNORECASE,
)
PRICE_RE = re.compile(
    r"\bharga|\bhrga|\bdiskon|\bpromo|\bgratis|\bfree\b"
    r"|\b\d+[kK]\b|\b\d+\s*(rb|ribu)\b",
    re.IGNORECASE,
)
STOCK_RE = re.compile(
    r"\b(ready|stok|habis|kosong|sold|restock|msh)\b|masih (gak|ga|nggak|engga|ada|ad)",
    re.IGNORECASE,
)
PURCHASE_RE = re.compile(
    r"\b(co|c/o|checkout|check\s*out|cek\s*out|otw|keranjang|borong|bungkus|bayar|gas|fix)\b"
    r"|\bspill\s+link\b|\blink\b|\bpesan|\border\b|\bmau\b|\bambil\b"
    r"|\b(pengen|pengin)\s+beli\b",
    re.IGNORECASE,
)
PRODUCT_NOUNS = re.compile(
    r"\b(celana|kaos|baju|jaket|sweater|sweter|hoodie|hudi|kemeja|dress|rok|tee|polo|outer|vest|cardigan|"
    r"crewneck|knitwear|henley|henly|ringer|chino|cino|jogger|longsleve|longsleeve|flanel|flannel|boxy|"
    r"airy|aery|singlet|pensil|pencil)\b",
    re.IGNORECASE,
)
FABRIC_RE = re.compile(r"\b(katun|kain|cotton|combed|fleece|polyester|dryfit|airy)\b", re.IGNORECASE)
PRODUCT_ASK = re.compile(
    r"\?|spil|spill|apa\b|ap\b|mana\b|kah\b|kan\b|bisa\b|boleh\b|msh\b|masih|mau\b|tolong|dong\b|"
    r"berap|brp|cek\b|lihat\b|liat\b|tengok|bahan|sablon|merk|merek|tebal|tipis|panjang|lebar|model|crop|"
    r"detail|motif|ketinggian|panjangnya|lebar|jogging|olahraga|ada\b|gak\b|ngga\b|nggak\b|dak\b|ada ga|ada ng|"
    r"gmna\b|gmana\b|gimana\b",
    re.IGNORECASE,
)
GIBBERISH_RE = re.compile(r"(.)\1{3,}")


def norm(t):
    return re.sub(r"\s+", " ", t.lower().replace("?", " ?")).strip()


def rule_for(text):
    t = norm(text)
    if not t:
        return "not_relevant"
    if re.search(r"[a-z]{2}", t) is None and not re.search(
        r"^\s*\d{1,3}\s+\d{2,3}\s*\??$|^\s*\d{1,3}\s*/\s*\d{1,3}\s*\??$|\d{2,3}\s+[a-z]", t
    ):
        return "not_relevant"
    if GIBBERISH_RE.search(t) and len(re.findall(r"[a-z0-9]", t)) >= 6:
        return "not_relevant"
    if any(w in t.split() for w in ("wkwk", "wkwkwk", "haha", "hehe", "first", "hadir", "fyp", "spam", "semoga dibaca", "pin dong")) or "join live" in t:
        if not re.search(r"\b(co|checkout|cek\s*out|pesan\b|beli|keranjang)\b", t) and len(t.split()) <= 5:
            return "not_relevant"
    if "follow" in t or "cek bio" in t or "mampir" in t:
        return "not_relevant"
    if re.search(r"(gratis|free|diskon|promo).*ongkir|ongkir.*(gratis|free|diskon|promo)", t):
        return "price_inquiry"
    if re.search(r"promosi", t) and "akun" in t:
        return "not_relevant"
    if re.search(r"pengiriman|ongkir|resi|qris|cod\b|pembayaran|payment|kurir|expedisi|dm\b|\bcht\b|\bchat\b|estimasi|hari\b", t) and not re.search(
        r"\bco\b|checkout|cek\s*out|done\b|udah\s+bayar", t
    ):
        return "not_relevant"

    has_body = bool(BODY_RE.search(t)) or bool(
        re.search(r"cocok|muat|muatin|mending|enaknya|minta\s*size|ambilin|fit\s*(atau|or)|(atau|or)\s+fit|slimfit|reguler fit|regular fit|loose|longgar|ketat|oversize|ovz|kegedean|kekecilan|kecilan|gedean|kepanjangan|kependekan|pasang?|pasin|ambil\s*(size|ukuran)|buncit|ngetat|ngefit|cukup", t)
    ) or bool(
        re.search(r"\b\d{1,3}\s*/\s*\d{1,3}\b|\b\d{2,3}\s+\d{1,3}\s+(size|ukuran)\b|\b(size|ukuran)\s+\d{2,3}\b", t)
    )
    has_color = any(c in t for c in COLORS)
    has_size = bool(SIZE_RE.search(t)) or bool(re.search(r"\b\d{2}\b", t)) or bool(
        re.search(r"\b(uk|ukuran|size|sz)\s*\d+[kK]?\b", t)
    )
    has_etalase = bool(
        re.search(r"\b(etalase|etlase|etelse|etalse|estalese|estalase|estelase|estlase|este|esto|eta|etl|ets|etls|tlse|et)\d*", t)
    )
    has_product_noun = bool(PRODUCT_NOUNS.search(t)) and bool(PRODUCT_ASK.search(t))
    has_fabric = bool(FABRIC_RE.search(t))

    if has_body and re.search(r"(panjang|lebar).*(brp|berap|berapa)|(brp|berap|berapa).*(panjang|lebar)", t) and re.search(r"cm|\d{2,3}", t) and not re.search(r"\b(bb|tb|ld|lp|lb|berat|tinggi)\b", t) and has_size:
        return "size_inquiry"
    if re.search(r"(spil|spill).*oversize|oversize.*(spil|spill)", t):
        return "product_inquiry"
    if re.search(
        r"\b(yg|yang|kknya|kakanya|kakaknya)\b.*\b(dipake|dipakai|pke|di pake|di pakai|pake|pakai)\b.*\b(size|ukuran|uk)\b",
        t,
    ) and re.search(r"apa|brp|berap", t) and not has_body:
        return "size_inquiry"

    if re.search(r"\bco\b", t) and not re.search(r"muat|fit|cocok|pas\b|bb\s*\d|tb\s*\d|kg\b|cm\b", t):
        return "purchase_intent"

    if re.search(r"beli\w*\s*(dmna|dimana|di mana)\b|\b(dmna|dimana|di mana)\b.*\bbeli\b", t):
        return "purchase_intent"

    if re.search(r"\b(checkout|check\s*out|cek\s*out|chkout|chekout|checkkout)\b", t):
        return "purchase_intent"

    if PURCHASE_RE.search(t) and not re.search(
        r"ambil\s+(size|ukuran|m\b|s\b|l\b|xl\b|xxl\b|xxxl\b)|mau\s+(nanya|tanya|tau|tahu|liat|lihat|nonton|order|beli|dipake|dipakai|pake|pakai|koment|komentar|omong|ngomong|bilang|yg|yang)|mau\s+cek\s+(liat|lihat|dulu|kak|bahan|barang)|tnyain",
        t,
    ) and not has_body:
        return "purchase_intent"

    if re.search(
        r"\b(cewe|cewek|cwo|cowok|cw)\b.*\b(bisa|buat|untuk)\b|\b(bisa|buat|untuk)\b.*\b(cewe|cewek|cwo|cowok|cw)\b",
        t,
    ) and not has_body:
        return "product_inquiry"

    if re.search(r"\bbb\b", t) and re.search(r"(brp|berap|berapa)", t) and not re.search(r"\d", t):
        return "size_inquiry"

    if PRICE_RE.search(t) and not re.search(r"\b(uk|ukuran|size|sz)\s*\d+[kK]\b", t) or re.search(r"pcs.*(brp|berap)|(brp|berap).*pcs", t):
        return "price_inquiry"

    if re.search(r"\b(brp|berapa|berap)\b", t) and not (
        has_etalase or has_size or has_color or has_body
    ):
        return "price_inquiry"

    if STOCK_RE.search(t):
        return "stock_availability"

    if re.search(r"cutting|cuttingan", t):
        return "product_inquiry"

    if has_size and re.search(r"\b(ld|lp|lb|lingkar)\b", t) and re.search(r"berap|brp|panjang|lebar", t) and not has_body:
        return "size_inquiry"

    if re.search(r"(beda|perbedaan)", t) and re.search(r"apa|gimana|gmna|kan|sama|sma|ama|\?", t) and not has_color and not re.search(
        r"\b(bb|tb|ld|lp|lb|kg|cm|berat|tinggi|lingkar|badan)\b|\b\d{2,3}\s*/\s*\d{2,3}\b|\b\d{1,3}\s+\d{2,3}\b", t
    ):
        return "product_inquiry"

    if re.search(
        r"\b(etalase|etlase|etelse|etalse|estalese|estalase|estelase|estlase|este|esto|eta|etl|ets|etls|tlse|et)\d*\s*(nya)?\s*(brp|berap|berapa|mana)\b",
        t,
    ):
        return "product_inquiry"

    if has_body:
        return "size_recommendation"

    if has_etalase and has_size and not re.search(r"\b(ukuran|size|uk|chart|s|m|l|xl|xxl|xxxl|free)\b", t):
        return "product_inquiry"
    if has_etalase and has_size:
        return "size_inquiry"
    if has_etalase:
        return "product_inquiry"

    if re.search(r"\b(spil|spill)\s+\d+\b|\b\d+\s+(spil|spill)\b", t):
        return "product_inquiry"

    if has_size and re.search(
        r"masih ada|masih ad|berap|brp|apa\b|ap\b|apq\b|apk\b|apaa|apa saja|apa aja|apakah|paling|panjang|lebar|"
        r"spil|spill|liat|lihat|gmna|gmana|gimana|chart|bsar|besar|kecil|kecul|custom|costum|zize|yang mana|yg mana|"
        r"kebesaran|kegedean|kekecilan|ketat|longgar|banding|bukan",
        t,
    ):
        return "size_inquiry"

    if (has_fabric or has_product_noun or re.search(
        r"bahan|sablon|merk|merek|kain|jatoh|furing|transparan|stretch|model|crop|adem|detail|motif|tebal|tipis|"
        r"panjang|lebar|lingkar|ketinggian|jogging|olahraga|logo|kusut|slim\s*fit|slimfit|buluan|nerawang",
        t,
    )) and not re.search(r"\bwarna\b", t):
        return "product_inquiry"

    if has_color:
        return "color_inquiry"

    if re.search(r"\b(no|nomor)\s*\d+\s*(ukuran|size)\b", t):
        return "size_inquiry"

    if has_fabric or has_product_noun or re.search(
        r"bahan|sablon|merk|merek|kain|jatoh|furing|transparan|stretch|model|crop|adem|detail|motif|tebal|tipis|panjang|lebar|lingkar|ketinggian|jogging|olahraga|logo|kusut|slim\s*fit|buluan|nerawang",
        t,
    ):
        return "product_inquiry"

    return "not_relevant"


MANUAL_FIXES = {
    "comment_000401": "not_relevant",
    "comment_000537": "size_recommendation",
    "comment_000564": "size_recommendation",
    "comment_000620": "size_inquiry",
    "comment_000672": "not_relevant",
    "comment_000734": "price_inquiry",
    "comment_000790": "product_inquiry",
    "comment_000797": "product_inquiry",
    "comment_000805": "not_relevant",
    "comment_000806": "product_inquiry",
    "comment_000837": "not_relevant",
    "comment_000879": "product_inquiry",
    "comment_000888": "not_relevant",
    "comment_000900": "size_recommendation",
    "comment_000907": "product_inquiry",
    "comment_000921": "product_inquiry",
    "comment_000944": "size_recommendation",
    "comment_000989": "purchase_intent",
    "comment_000990": "product_inquiry",
    "comment_001021": "price_inquiry",
    "comment_001032": "size_inquiry",
    "comment_001060": "product_inquiry",
    "comment_001072": "product_inquiry",
    "comment_001124": "not_relevant",
    "comment_001189": "size_inquiry",
    "comment_001241": "product_inquiry",
    "comment_001249": "product_inquiry",
    "comment_001251": "not_relevant",
    "comment_001221": "product_inquiry",
    "comment_001386": "size_recommendation",
    "comment_001469": "not_relevant",
    "comment_001499": "color_inquiry",
    "comment_001507": "color_inquiry",
    "comment_001510": "product_inquiry",
    "comment_001518": "product_inquiry",
    "comment_001519": "product_inquiry",
    "comment_001524": "product_inquiry",
    "comment_001538": "product_inquiry",
    "comment_001592": "product_inquiry",
    "comment_001595": "product_inquiry",
    "comment_001598": "product_inquiry",
    "comment_001600": "size_inquiry",
    "comment_001632": "product_inquiry",
    "comment_001635": "product_inquiry",
    "comment_001569": "product_inquiry",
    "comment_001575": "product_inquiry",
    "comment_001646": "product_inquiry",
    "comment_001666": "product_inquiry",
    "comment_001701": "size_recommendation",
    "comment_001724": "product_inquiry",
    "comment_001727": "size_inquiry",
    "comment_001729": "product_inquiry",
    "comment_001743": "product_inquiry",
    "comment_001746": "size_inquiry",
    "comment_001769": "product_inquiry",
    "comment_001807": "product_inquiry",
    "comment_001818": "product_inquiry",
    "comment_001853": "purchase_intent",
    "comment_001880": "not_relevant",
}


def main():
    df = pd.read_csv(SRC, encoding="utf-8-sig")
    rows = []
    for r in df.itertuples():
        rows.append(
            {
                "comment_id": r.comment_id,
                "text": r.text,
                "intent_lama": r.intent,
                "sentiment": r.sentiment,
                "intent_baru": MANUAL_FIXES.get(r.comment_id, rule_for(str(r.text))),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False, encoding="utf-8-sig")

    print("total:", len(out))
    print("\nintent baru:")
    print(out["intent_baru"].value_counts().to_string())
    print("\nmapping lama -> baru:")
    tab = pd.crosstab(out["intent_lama"], out["intent_baru"])
    print(tab.to_string())
    print("\nsentiment (dipertahankan):")
    print(out["sentiment"].value_counts().to_string())


if __name__ == "__main__":
    main()