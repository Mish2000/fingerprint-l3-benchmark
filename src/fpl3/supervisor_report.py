"""Presentation of fixed decisions; no threshold sweep or biometric execution."""

import csv
import io
from pathlib import Path

from .io import digest, read_json, write_bytes, write_json
from .supervisor import assess_supervisor


def rate_text(row):
    if row["rate"] is None:
        return "לא מוגדר (מכנה 0)"
    return f"{row['rate_numerator']}/{row['rate_denominator']} ({row['rate']:.2%})"


def report_markdown(report, profile, timings):
    v = report["views"]
    def table(rows, negative=False):
        accepted = "קבלות שגויות" if negative else "MATCH"
        rejected = "דחיות לפי ציון" if negative else "NON_MATCH"
        header = f"| אוכלוסייה | {accepted} | {rejected} | כשלי עיבוד | מכנה | שיעור {'קבלה שגויה' if negative else 'התאמה'} |\n"
        header += "|---|---:|---:|---:|---:|---|\n"
        return header + "\n".join(f"| {r['view']} | {r['MATCH']} | {r['NON_MATCH']} | {r['PROCESSING_FAILURE']} | {r['total']} | {rate_text(r)} |" for r in rows)
    n = report["subjects"]
    role = "הערכה ראשית" if report["role"] == "evaluation" else "בדיקת מימוש בפיתוח"
    stage_times = timings["matching_seconds"]
    return f"""# דוח ששת השלבים — P1

**{role} | ASM-F40-SIFT-SPATIAL | SD300B מקורי, 1000 PPI | {n} נבדקים, {n * 10} אצבעות**

כלל החלטה קבוע: `score {profile['comparison']} {profile['threshold']!r}`.
הסף נבחר מ־200 ציוני impostor מאומתים של חמשת נבדקי הפיתוח בלבד: {profile['false_accepts']}/200 קבלות שגויות.
זהו כיוון של מדיניות החלטה במדגם פיתוח קטן ומוכר. היעד עד 2/200 הוגדר במפרט צעד 02 ואינו הבטחה ל־1% באוכלוסייה.

## 1. מספר רשומות הקלט

{report['plain_images']} תמונות PLAIN ו־{report['roll_images']} תמונות ROLL. זהויות, גיבובים, ממדים וכל עשרת מיקומי האצבעות אומתו.
המקור הוא סריקות כרטיסי דיו. לא בוצעו resize ל־500 PPI, חיתוך חדש או שיפור תמונה נוסף; פעולות SIFT ההיסטוריות נשמרו.

## 2. PLAIN SELF

{table(v[:1])}

## 3. ROLL SELF

{table(v[1:2])}

SELF משתמש במתאם האמיתי על שני חילוצים נפרדים מאותה תמונה. אלו אינם שתי רכישות ביומטריות עצמאיות.
NON_MATCH או כשל עיבוד ב־SELF מוציאים את יחידת האצבע מן המבט המסונן. רשימת הסיבות נשמרת ב־eligibility.json.

## 4. התאמת זהויות ואצבעות

{report['metadata_mated_units']} יחידות PLAIN–ROLL נקשרו לפי זהות ואצבע אנטומית. מספר השורדות שני SELF הוא **X={report['X']}**.
מיפוי PLAIN: קוד 11 לאצבע 1, קוד 12 לאצבע 6; יתר קודי האצבע היחידה נשמרים. 13/14 אינם משתתפים.
התאמה במטא־דאטה אינה הצלחת matcher. אין חוסרים, החלפת נבדקים או שינוי באמת המידה בעקבות SELF.

## 5. PLAIN מול ROLL של אותו נבדק ואותה אצבע

{table(v[2:4])}

ALL הוא המדד הלא־מסונן להשוואה. SELF-FILTERED הוא מבט על אותן תוצאות. כישלון PLAIN–ROLL אינו עילת סינון.

## 6. PLAIN מול ROLL של הנבדק הבא באותה אצבע

{table(v[4:6], negative=True)}

הרשימה הקיימת נשמרה בסדרה ובסדר: הבא הוא הבא ברשימת הנבדקים, עם סגירה מחזורית מן האחרון לראשון.
נשמרו כל {n * 10} זוגות הבסיס. במבט המסונן נדרשת זכאות SELF של שתי יחידות האצבע: **Y={report['Y']}**.
לא מסדרים מחדש נבדקים ולא מחפשים את הבא ששרד. שיעור זה מתייחס לניסוי next-subject שנקבע; אין להניח עצמאות בין זוגות או להסיק ממנו אפס סיכון באוכלוסייה.

## זמן ושימוש חוזר

| מדידה | שניות |
|---|---:|
| קריאת קלט | {timings['input_seconds']:.3f} |
| גלאי Survey, שני חילוצים למקור | {timings['detection_seconds']:.3f} |
| הפקת SIFT | {timings['description_seconds']:.3f} |
| PLAIN SELF matching | {stage_times['plain_self']:.3f} |
| ROLL SELF matching | {stage_times['roll_self']:.3f} |
| Genuine matching | {stage_times['plain_roll_mated']:.3f} |
| Next-subject matching | {stage_times['plain_roll_next_subject_non_mated']:.3f} |
| טעינת מודל ומתאמים | {timings['worker_load_seconds']:.3f} |
| תקורת worker מצטברת | {timings['worker_overhead_seconds']:.3f} |
| זמן קיר של תיאום, הרצה ואימות | {timings['orchestrator_wall_seconds']:.3f} |

{timings['fresh_extractions']} חילוצים טריים; {timings['cache_hits']} פגיעות cache; {timings['matcher_invocations']} קריאות matcher.
הפקות צד a ממוחזרות בתוך הריצה לזוגות genuine ושליליים. ציונים היסטוריים לא מוצגים כקריאות חדשות.
זמני worker מצטברים על פני תהליכים מקבילים ולכן אינם סכום של זמן הקיר. ALL/FILTERED אינם מכפילים זמן matching.
עלות החילוץ הכפול היא עלות בדיקת SELF, ואינה עלות הכרחית לכל השוואה עתידית.

## מקורות, החלטות ומגבלות

מבנה ששת הסעיפים וניקוי לפי SELF נתמכים בהודעות המנחה המצוטטות במפרט שהמשתמש סיפק.
תיאור next-subject מופיע בדוח מיכאל ובהבהרת המשתמש. המחזוריות, כלל הסף, אי־הזיווג מחדש והצגת ALL/FILTERED הם החלטות המפרט הנוכחי.
אין לייחס למנחה אישור של ההרכבה האלגוריתמית או של כל החלטת מימוש.

P1 הוא הרכבה מקומית: גלאי Survey f40 נלמד, מתאר SIFT ומתאם spatial. AI משתתף בחיזוי מיקומי נקבוביות; הסימונים אינם אמת קרקע אנטומית.
משקולות, preprocessing, גאומטריה ונוסחת הציון נשמרו. 0.65 של הגלאי ו־0.7 של יחס המרחקים אינם סף זהות.
חמשת נבדקי הפיתוח אינם חופפים לרשימת ה־50. היסטוריית החשיפה הקודמת נשמרה; אין טענה שקבוצת ההערכה מעולם לא נצפתה.
SD300B/C הם סריקות קשורות של אותם כרטיסים. כאן הוערך SD300B בלבד; אין הכללה מבוססת לחיישנים אחרים או לטביעות חיות.
לא בוצעו sweep ספים, אימון, DP, P2 או הערכה בשיטה/רזולוציה נוספת. השלמות נמדדת בכיסוי וראיות תקינות, ללא דרישה ל־98%, ל־100% SELF או לאפס קבלות שגויות.
"""


def write_report(prepared, local_path, run, output):
    validation = assess_supervisor(prepared, local_path, run)
    report = read_json(Path(run) / "report.json")
    profile = read_json(Path(prepared) / "decision_profile.json")
    timings = read_json(Path(run) / "timings.json")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_bytes(output / "report_he.md", report_markdown(report, profile, timings).encode("utf-8"))
    write_json(output / "eligibility.json", report["eligibility"])
    fields = ["pair_id", "kind", "left", "right", "ground_truth", "status", "score", "decision", "self_eligible", "reason", "failure_stage", "matcher_invoked", "score_origin", "comparison_seconds"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in report["results"]:
        writer.writerow({k: row["timings"][k] if k == "comparison_seconds" else row.get(k) for k in fields})
    write_bytes(output / "results_opaque.csv", stream.getvalue().encode("utf-8-sig"))
    write_json(output / "verification.json", {**validation, "run_seal_sha256": digest(Path(run) / "complete.json"),
               "report_source_sha256": digest(Path(run) / "report.json"), "decision_sha256": digest(Path(prepared) / "decision_profile.json")})
    return {"approved": True, "role": report["role"], "pairs": len(report["results"]), "X": report["X"], "Y": report["Y"]}
