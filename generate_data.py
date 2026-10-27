#!/usr/bin/env python3
"""
Brassy LMS - dummy dataset generator.

Creates one CSV per table (file name = table name, header = exact field names
from the Dummy Dataset Collection Guide) in ./brassy_data/ and a README.md
with the row count of every table.

    pip install faker
    python generate_data.py                # writes ./brassy_data/*.csv
    python generate_data.py --seed 7       # different (but reproducible) data

Business rules from Section 6 of the guide are enforced while generating, and
parents are always created before children (Section 4).
"""
import argparse
import csv
import json
import os
import random
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from faker import Faker

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
N_STUDENTS, N_INSTRUCTORS, N_ADMINS = 285, 12, 3        # 300 users
N_ENROLMENTS = 850
MAX_PER_STUDENT = 4          # guide: 'some students enrol in 2-3 courses'
N_QUIZ = 220
NOW = datetime.now().replace(microsecond=0)


def add_months(d, n):
    m = d.month - 1 + n
    return d.replace(year=d.year + m // 12, month=m % 12 + 1, day=1)


# data window: the 18 months before the current month (+ current month)
START = add_months(NOW.replace(day=1, hour=0, minute=0, second=0), -18)
# enrolment peaks around typical batch-start months (Jan/Feb, Jun/Jul)
MONTH_NUM_W = {1: 8, 2: 9, 3: 4, 4: 3, 5: 4, 6: 8, 7: 10, 8: 5, 9: 3, 10: 4, 11: 3, 12: 2}

COLS = {
    "users": "id first_name last_name email password gender designation bio profile_photo location phone "
             "reset_password_token reset_password_send_at reset_password_expires reset_password_at website "
             "twitter facebook linkedin youtube role email_confirmed email_confirmed_at instructor_request "
             "instructor_request_confirmed instructor_request_confirmed_at instructor_status instructor_subject "
             "instructor_description status is_profile_public college_name deg_dept reg_num year_of_graduation "
             "created_at updated_at",
    "categories": "id name slug created_at updated_at",
    "task_type": "id title created_at updated_at",
    "quiz": "id question options quiz_type correct_answer courses isCheckbox points created_at updated_at",
    "coupons": "id code discount exp_date status deleted_at active_for_full_site created_at updated_at",
    "partners": "id name partner_image created_at updated_at",
    "subscriptions": "id email active created_at updated_at",
    "testimonials": "id image_url name designation description created_at updated_at",
    "enquiries": "id name email phone college_name location mode message domain date_of_joining enquiry_type "
                 "duration education_status slot batch_startdate register_num deg_dept created_at updated_at",
    "company_enquire": "id name phone_no email_id company job_description created_at updated_at",
    "courses": "id title slug short_desc overview latest_price before_price lessons duration image access_time "
               "requirements what_you_will_learn who_is_this_course_for userId catId approved in_home_page "
               "in_home_page_set_at is_class created_at updated_at",
    "videos": "id group_name title thumb video video_length is_preview short_id assets_zip userId courseId "
              "created_at updated_at",
    "course_assets": "id lecture_name lecture_file courseId created_at updated_at",
    "favourites": "id userId courseId created_at updated_at",
    "tasks": "id created_at updated_at",
    "batches": "id name instructor_id batchNo isActive isUpcoming created_at updated_at",
    "instructor_earnings": "id earnings userId courseId status created_at updated_at",
    "work_sessions": "id userId date start_time end_time session_title summary session_timing session_status "
                     "status edit_description is_edited is_requested created_at updated_at",
    "enrolments": "id bought_price payment_method buyer_name buyer_email buyer_avatar types userId courseId "
                  "start_date end_date amount_paid balance_amount status progress_status certificate_downloads "
                  "enrolment_title enrolment_duration payment_split phonepe_order_id txn_id college_name deg_dept "
                  "reg_num assigned_study_materials created_at updated_at",
    "payment_invoices": "id userId enrolmentId amount_paid amount status title due_date paid_date is_active "
                        "created_at updated_at",
    "reward_points": "id enrolmentId userId points status expired_on created_at updated_at",
    "used_reward_points": "id enrolmentId userId points status created_at updated_at",
    "attendance_records": "id enrolmentId userId attendance_date status created_at updated_at",
    "batch_members": "id batchId enrolmentId created_at updated_at",
    "certificate_downloads": "id enrolmentId certificateId certificatePdfUrl createdAt updatedAt",
    "course_progresses": "id finished userId courseId enrolmentId videoId quizType points created_at updated_at",
    "task_progress": "id task_name task_file task_type userId courseId taskId status duration start_date "
                     "end_date created_at updated_at",
    "transactions": "id userId enrolmentId paymentInvoiceId amount_paid status mode online_transaction_id "
                    "payment_name due_date paid_date created_at updated_at",
}
COLS = {t: c.split() for t, c in COLS.items()}

# creation order (parents first) - also used by load_to_mysql.py
ORDER = ["users", "categories", "task_type", "quiz", "coupons", "partners", "subscriptions", "testimonials",
         "enquiries", "company_enquire", "courses", "videos", "course_assets", "favourites", "tasks", "batches",
         "instructor_earnings", "work_sessions", "enrolments", "payment_invoices", "reward_points",
         "used_reward_points", "attendance_records", "batch_members", "certificate_downloads",
         "course_progresses", "task_progress", "transactions"]

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
fake = Faker("en_IN")
TABLES = {}


def uid():
    return str(uuid.UUID(int=random.getrandbits(128), version=4))


def rdt(a, b):
    """random datetime between a and b"""
    if b <= a:
        return a
    return a + timedelta(seconds=random.randint(0, int((b - a).total_seconds())))


def cap(d, hi=None):
    return min(d, hi or NOW)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def blank(table):
    return {c: None for c in COLS[table]}


def pick_month_date(first_offset=1):
    """random datetime weighted by seasonal enrolment peaks; never in the last 6 days"""
    months, weights = [], []
    m = add_months(START, first_offset)
    while m <= NOW:
        months.append(m)
        weights.append(MONTH_NUM_W[m.month])
        m = add_months(m, 1)
    m = random.choices(months, weights)[0]
    last = min(add_months(m, 1) - timedelta(seconds=1), NOW - timedelta(days=6))
    return rdt(m, last).replace(hour=random.randint(8, 20), minute=random.randint(0, 59), second=0)


def phone():
    return random.choice("6789") + "".join(random.choices("0123456789", k=9))


def clean(s):
    return re.sub(r"[^A-Za-z]", "", s) or "user"


def fake_hash():
    return "Dummy@" + str(random.randint(1000, 9999))


def maybe(p, value):
    return value if random.random() < p else None


def write_csv(outdir, table):
    path = os.path.join(outdir, table + ".csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLS[table])
        for row in TABLES[table]:
            out = []
            for c in COLS[table]:
                v = row[c]
                if v is None:
                    v = ""
                elif isinstance(v, bool):
                    v = int(v)
                elif isinstance(v, datetime):
                    v = v.strftime("%Y-%m-%d %H:%M:%S")
                out.append(v)
            w.writerow(out)


CITIES = ["Chennai", "Coimbatore", "Madurai", "Tirunelveli", "Trichy", "Salem", "Bengaluru", "Hyderabad",
          "Kochi", "Pune", "Mumbai", "Delhi", "Kolkata", "Vellore", "Erode"]
DEGREES = ["B.E CSE", "B.Tech IT", "B.Tech AI&DS", "B.E ECE", "B.Sc CS", "BCA", "MCA", "B.E EEE", "B.E Mech"]
COLLEGE_SUFFIX = ["Institute of Technology", "College of Engineering", "Arts & Science College",
                  "Polytechnic College", "University College"]
PAY_METHODS = ["UPI", "Card", "Cash", "PhonePe", "NetBanking"]

# --------------------------------------------------------------------------
# Step 1 - users, categories, task_type, quiz, coupons, partners, ...
# --------------------------------------------------------------------------
def build_users():
    rows, emails = [], set()

    def new_user(role, created):
        r = blank("users")
        first, last = clean(fake.first_name()), clean(fake.last_name())
        email = f"{first}.{last}{random.randint(1, 999)}@example.com".lower()
        while email in emails:
            email = f"{first}.{last}{random.randint(1, 99999)}@example.com".lower()
        emails.add(email)
        r.update(id=uid(), first_name=first, last_name=last, email=email, password=fake_hash(),
                 gender=maybe(0.95, random.choices(["Male", "Female", "Other"], [48, 49, 3])[0]),
                 location=maybe(0.85, random.choice(CITIES)), phone=maybe(0.9, phone()),
                 profile_photo=maybe(0.6, f"/uploads/avatars/{uid()[:8]}.png"), role=role,
                 email_confirmed=True if role != "student" else random.random() < 0.88,
                 instructor_request=False, instructor_request_confirmed=False, instructor_status=False,
                 status=random.random() < 0.93, is_profile_public=random.random() < 0.8,
                 created_at=created)
        r["email_confirmed_at"] = created + timedelta(minutes=random.randint(1, 2880)) if r["email_confirmed"] else None
        r["updated_at"] = rdt(created, NOW) if random.random() < 0.5 else created
        if random.random() < 0.04:  # a few password-reset records
            sent = rdt(created, NOW)
            r["reset_password_token"] = uid()
            r["reset_password_send_at"] = sent
            r["reset_password_expires"] = sent + timedelta(hours=1)
            r["reset_password_at"] = maybe(0.5, sent + timedelta(minutes=random.randint(2, 50)))
            r["updated_at"] = max(r["updated_at"], r["reset_password_at"] or sent)
        rows.append(r)
        return r

    for _ in range(N_ADMINS):
        a = new_user("admin", START + timedelta(days=random.randint(0, 3)))
        a["designation"] = "Platform Administrator"
    for _ in range(N_INSTRUCTORS):
        i = new_user("instructor", START + timedelta(days=random.randint(0, 10)))
        i.update(designation=random.choice(["Senior Data Analyst", "Full Stack Developer", "UX Lead",
                                            "Digital Marketing Manager", "Business Analyst Lead",
                                            "Technical Trainer", "Database Consultant", "Product Designer"]),
                 bio=fake.paragraph(nb_sentences=3),
                 linkedin=f"https://www.example.com/in/{i['first_name']}-{i['last_name']}".lower(),
                 website=maybe(0.4, f"https://{i['first_name']}{i['last_name']}.example.com".lower()),
                 twitter=maybe(0.3, f"https://example.com/{i['first_name']}".lower()),
                 youtube=maybe(0.2, f"https://example.com/yt/{i['last_name']}".lower()),
                 instructor_request=True, instructor_request_confirmed=True,
                 instructor_request_confirmed_at=i["created_at"] + timedelta(days=random.randint(0, 3)),
                 instructor_status=True,
                 instructor_description=fake.sentence(nb_words=12))
        i["updated_at"] = max(i["updated_at"], i["instructor_request_confirmed_at"])
    for _ in range(N_STUDENTS):
        created = max(START, pick_month_date(0) - timedelta(days=random.randint(0, 25)))
        s = new_user("student", created)
        s.update(college_name=maybe(0.92, f"{clean(fake.last_name())} {random.choice(COLLEGE_SUFFIX)}"),
                 deg_dept=maybe(0.9, random.choice(DEGREES)),
                 reg_num=maybe(0.85, str(random.randint(10**11, 10**12 - 1))),
                 year_of_graduation=maybe(0.9, random.choice([2025, 2026, 2026, 2027, 2027, 2028])),
                 bio=maybe(0.1, fake.sentence(nb_words=10)),
                 linkedin=maybe(0.15, f"https://www.example.com/in/{s['first_name']}{random.randint(1, 99)}".lower()))
        if random.random() < 0.03:  # some pending instructor requests that were never approved
            s["instructor_request"] = True
    random.shuffle(rows)
    TABLES["users"] = rows


CATEGORY_COURSES = {
    "Full Stack Development": ["Full Stack Web Development with MERN", "Full Stack Development with Java & Spring Boot",
                               "Full Stack Development with Python & Django", "Front-End Development with React",
                               "Backend Development with Node.js", "HTML, CSS & JavaScript Foundations"],
    "UI/UX Design": ["UI/UX Design with Figma", "Product Design Fundamentals", "Design Thinking Workshop",
                     "UX Research & Usability Testing", "Responsive Web Design", "Mobile App UI Design"],
    "Data Analyst": ["Data Analyst Bootcamp", "Data Analysis with Python & Pandas", "Data Visualization with Power BI",
                     "Excel for Data Analysis", "Tableau for Data Analysts", "Statistics for Data Analysis"],
    "Digital Marketing": ["Digital Marketing Masterclass", "SEO & Content Marketing", "Social Media Marketing",
                          "Google Ads & Performance Marketing", "Email Marketing & Automation",
                          "Marketing Analytics with Google Analytics"],
    "Business Analyst": ["Business Analyst Bootcamp", "Business Analysis Fundamentals", "Requirement Gathering & Documentation",
                         "Agile & Scrum for Business Analysts", "Power BI for Business Analysts", "SQL for Business Analysts"],
    # supporting categories (the guide asks for 8-10 categories)
    "Python Programming": ["Python Programming Masterclass", "Python Problem Solving for Interviews"],
    "Database & SQL": ["SQL for Data Analysts", "MySQL Database Administration"],
    "Placement Training": ["Quantitative Aptitude & Reasoning", "Interview Skills & Resume Building"],
}
# category -> quiz_type used for quiz rows in course_progresses
CAT_QUIZ_TYPE = {"Python Programming": "Python", "Database & SQL": "SQL", "Placement Training": "Aptitude",
                 "Data Analyst": "SQL", "Business Analyst": "Aptitude"}


def build_simple_tables():
    # categories
    rows = []
    for name in CATEGORY_COURSES:
        r = blank("categories")
        c = START + timedelta(days=random.randint(0, 6), hours=random.randint(0, 23))
        r.update(id=uid(), name=name, slug=slugify(name), created_at=c, updated_at=c)
        rows.append(r)
    TABLES["categories"] = rows

    # task_type
    rows = []
    for t in ["Assignment", "Mini Project", "Case Study", "Capstone Project", "Practice Lab", "Mock Test"]:
        r = blank("task_type")
        c = START + timedelta(days=random.randint(0, 6))
        r.update(id=uid(), title=t, created_at=c, updated_at=c)
        rows.append(r)
    TABLES["task_type"] = rows

    # tasks (only id + timestamps until the guide confirms the field list)
    rows = []
    for _ in range(40):
        r = blank("tasks")
        c = rdt(START + timedelta(days=15), NOW - timedelta(days=30))
        r.update(id=uid(), created_at=c, updated_at=rdt(c, NOW) if random.random() < 0.3 else c)
        rows.append(r)
    TABLES["tasks"] = rows

    # coupons
    rows, codes = [], set()
    for i in range(25):
        code = random.choice(["WELCOME", "SAVE", "FEST", "LEARN", "EARLY", "STUDENT", "NEWYEAR", "BATCH"]) + \
               str(random.choice([5, 10, 15, 20, 25, 30, 40]))
        while code in codes:
            code += random.choice("ABCDEFGH")
        codes.add(code)
        c = rdt(START + timedelta(days=10), NOW - timedelta(days=5))
        exp = c + timedelta(days=random.randint(30, 365))
        r = blank("coupons")
        r.update(id=uid(), code=code, discount=float(random.choice([5, 10, 15, 20, 25, 30, 40, 50])),
                 exp_date=exp, status=exp > NOW and random.random() < 0.85,
                 deleted_at=maybe(0.1, rdt(c, NOW)), active_for_full_site=random.random() < 0.4,
                 created_at=c, updated_at=rdt(c, NOW) if random.random() < 0.4 else c)
        if r["deleted_at"]:
            r["updated_at"] = max(r["updated_at"], r["deleted_at"])
        rows.append(r)
    TABLES["coupons"] = rows

    # partners
    rows = []
    for _ in range(20):
        c = rdt(START, NOW - timedelta(days=20))
        name = fake.company()
        r = blank("partners")
        r.update(id=uid(), name=name, partner_image=f"/uploads/partners/{slugify(name)}.png",
                 created_at=c, updated_at=c)
        rows.append(r)
    TABLES["partners"] = rows

    # subscriptions
    rows, seen = [], set()
    for _ in range(100):
        e = f"{clean(fake.first_name())}{random.randint(1, 9999)}@example.com".lower()
        if e in seen:
            continue
        seen.add(e)
        c = rdt(START, NOW)
        r = blank("subscriptions")
        r.update(id=uid(), email=e, active=random.random() < 0.85, created_at=c,
                 updated_at=rdt(c, NOW) if random.random() < 0.3 else c)
        rows.append(r)
    TABLES["subscriptions"] = rows

    # testimonials
    quotes = ["The hands-on projects helped me crack my first interview.",
              "Instructors explain concepts clearly and are always available for doubts.",
              "Great course structure; the weekly assignments kept me consistent.",
              "I moved from a non-IT background to a data role after this program.",
              "Live classes and recorded sessions made it easy to learn at my own pace.",
              "The placement training gave me real confidence for aptitude rounds."]
    rows = []
    for _ in range(25):
        c = rdt(START + timedelta(days=60), NOW)
        name = f"{clean(fake.first_name())} {clean(fake.last_name())}"
        r = blank("testimonials")
        r.update(id=uid(), image_url=f"/uploads/testimonials/{uid()[:8]}.jpg", name=name,
                 designation=random.choice(["Data Analyst", "Software Engineer", "Student", "UI/UX Designer",
                                            "Business Analyst", "Digital Marketer", "Web Developer"]),
                 description=" ".join(random.sample(quotes, 2)), created_at=c, updated_at=c)
        rows.append(r)
    TABLES["testimonials"] = rows

    # enquiries
    domains = list(CATEGORY_COURSES)
    msgs = ["Please share the fee structure.", "Do you provide placement assistance?",
            "Need details about the next batch.", "Is a demo class available?", "Interested in weekend batches."]
    rows = []
    for _ in range(80):
        c = rdt(START, NOW)
        r = blank("enquiries")
        nm = f"{clean(fake.first_name())} {clean(fake.last_name())}"
        r.update(id=uid(), name=nm, email=maybe(0.85, f"{nm.split()[0]}{random.randint(1, 999)}@example.com".lower()),
                 phone=phone(), college_name=maybe(0.7, f"{clean(fake.last_name())} {random.choice(COLLEGE_SUFFIX)}"),
                 location=maybe(0.8, random.choice(CITIES)), mode=maybe(0.9, random.choice(["online", "offline"])),
                 message=maybe(0.7, random.choice(msgs)), domain=random.choice(domains),
                 date_of_joining=maybe(0.6, c + timedelta(days=random.randint(5, 60))),
                 enquiry_type=random.choice(["Course Enquiry", "Internship", "Demo Class", "Placement Training"]),
                 duration=maybe(0.7, random.choice(["1 Month", "2 Months", "3 Months", "6 Months"])),
                 education_status=maybe(0.8, random.choice(["Student", "Graduate", "Working Professional"])),
                 slot=maybe(0.7, random.choice(["Morning", "Afternoon", "Evening", "Weekend"])),
                 batch_startdate=maybe(0.5, (c + timedelta(days=random.randint(7, 45))).strftime("%Y-%m-%d")),
                 register_num=maybe(0.3, str(random.randint(10**11, 10**12 - 1))),
                 deg_dept=maybe(0.5, random.choice(DEGREES)), created_at=c, updated_at=c)
        rows.append(r)
    TABLES["enquiries"] = rows

    # company_enquire
    rows = []
    for _ in range(40):
        c = rdt(START, NOW)
        nm = f"{clean(fake.first_name())} {clean(fake.last_name())}"
        r = blank("company_enquire")
        r.update(id=uid(), name=nm, phone_no=phone(),
                 email_id=maybe(0.9, f"{nm.split()[0]}.hr{random.randint(1, 99)}@example.com".lower()),
                 company=maybe(0.95, fake.company()),
                 job_description=maybe(0.8, random.choice(["Hiring Data Analyst freshers", "Need Python developers",
                                                           "Campus drive for 2026 batch", "Looking for cloud interns",
                                                           "Hiring junior data scientists", "Support engineers (freshers)"])),
                 created_at=c, updated_at=rdt(c, NOW) if random.random() < 0.2 else c)
        rows.append(r)
    TABLES["company_enquire"] = rows


# ---- quiz question bank ---------------------------------------------------
def mk_options(correct, wrongs):
    opts = []
    for w in wrongs:
        if w != correct and w not in opts:
            opts.append(w)
    opts = opts[:3] + [correct]
    random.shuffle(opts)
    return opts


def num_wrongs(a, step=1):
    cands = [a + k * step for k in range(-4, 5) if k != 0 and a + k * step >= 0]
    return [str(x) for x in random.sample(cands, 3)]


def gen_aptitude():
    t = random.choice(["pct", "avg", "si", "dist", "ratio", "profit"])
    if t == "pct":
        x, y = random.choice([5, 10, 15, 20, 25, 30, 40, 60, 75]), random.choice(range(40, 1001, 20))
        a = x * y // 100
        return f"What is {x}% of {y}?", str(a), num_wrongs(a, max(1, a // 8))
    if t == "avg":
        n = [random.randint(10, 90) for _ in range(3)]
        n.append(random.randint(10, 90))
        n[3] += (4 - sum(n) % 4) % 4
        a = sum(n) // 4
        return f"Find the average of {n[0]}, {n[1]}, {n[2]} and {n[3]}.", str(a), num_wrongs(a, 2)
    if t == "si":
        p, r, y = random.choice(range(1000, 20001, 1000)), random.randint(5, 12), random.randint(1, 5)
        a = p * r * y // 100
        return f"Find the simple interest on Rs. {p} at {r}% per annum for {y} years.", str(a), num_wrongs(a, 50)
    if t == "dist":
        s, h = random.choice(range(30, 121, 10)), random.randint(2, 8)
        a = s * h
        return f"A vehicle travels at {s} km/h for {h} hours. What distance does it cover (in km)?", str(a), num_wrongs(a, 10)
    if t == "ratio":
        a1, b1 = random.choice([(2, 3), (3, 4), (5, 7), (4, 9), (3, 5), (2, 5)])
        k = random.randint(2, 12)
        return f"The ratio of A to B is {a1}:{b1}. If A = {a1 * k}, what is B?", str(b1 * k), num_wrongs(b1 * k, k)
    cp, p = random.choice(range(100, 2001, 100)), random.choice([10, 20, 25, 40, 50])
    a = cp * (100 + p) // 100
    return f"An article bought for Rs. {cp} is sold at a profit of {p}%. Find the selling price (in Rs.).", str(a), num_wrongs(a, max(5, cp // 20))


WORDS = ["python", "analytics", "dataset", "cloud", "pandas", "server", "learning", "database", "network",
         "dashboard", "student", "campus", "report", "pipeline", "feature"]


def gen_python():
    t = random.choice(["len", "floordiv", "mod", "pow", "sumrange", "upper", "index", "max", "min", "rev", "expr"])
    w = random.choice(WORDS)
    a, b = random.randint(10, 99), random.randint(2, 9)
    lst = [random.randint(1, 50) for _ in range(random.randint(4, 6))]
    if t == "len":
        v = len(w)
        return f"What is the output of len('{w}')?", str(v), num_wrongs(v)
    if t == "floordiv":
        return f"What is the output of {a} // {b}?", str(a // b), num_wrongs(a // b)
    if t == "mod":
        v = a % b
        return f"What is the output of {a} % {b}?", str(v), num_wrongs(v)
    if t == "pow":
        n = random.randint(3, 10)
        return f"What is the output of 2 ** {n}?", str(2 ** n), num_wrongs(2 ** n, 2 ** (n - 2))
    if t == "sumrange":
        n = random.randint(4, 15)
        v = n * (n - 1) // 2
        return f"What is the output of sum(range({n}))?", str(v), num_wrongs(v, 2)
    if t == "upper":
        return f"What is the output of '{w}'.upper()?", w.upper(), [w.lower(), w.title(), w, "Error"]
    if t == "index":
        i = random.randint(0, len(lst) - 1)
        return f"What is the output of {lst}[{i}]?", str(lst[i]), num_wrongs(lst[i])
    if t == "max":
        return f"What is the output of max({lst})?", str(max(lst)), num_wrongs(max(lst))
    if t == "min":
        return f"What is the output of min({lst})?", str(min(lst)), num_wrongs(min(lst))
    if t == "rev":
        return f"What is the output of '{w}'[::-1]?", w[::-1], [w, w.upper(), w[1:], w[:-1]]
    v = a ** 2 + b
    return f"What is the output of {a} ** 2 + {b}?", str(v), num_wrongs(v, 10)


SQL_Q = [
    ("Which SQL clause is used to filter rows after grouping?", "HAVING", ["WHERE", "GROUP BY", "ORDER BY"]),
    ("Which keyword removes duplicate rows from a result set?", "DISTINCT", ["UNIQUE", "DIFFERENT", "REMOVE"]),
    ("Which JOIN returns all rows from the left table and matching rows from the right table?", "LEFT JOIN", ["INNER JOIN", "RIGHT JOIN", "CROSS JOIN"]),
    ("Which command removes all rows from a table but keeps its structure?", "TRUNCATE", ["DROP", "REMOVE", "CLEAR"]),
    ("Which aggregate function returns the number of rows?", "COUNT()", ["SUM()", "TOTAL()", "ROWS()"]),
    ("Which constraint ensures all values in a column are different?", "UNIQUE", ["CHECK", "DEFAULT", "INDEX"]),
    ("Which statement is used to modify existing records?", "UPDATE", ["MODIFY", "CHANGE", "ALTER ROW"]),
    ("A foreign key refers to which key of another table?", "Primary key", ["Candidate key only", "Composite index", "Surrogate view"]),
    ("Which operator is used to search for a pattern in a column?", "LIKE", ["MATCH", "SEARCH", "FIND"]),
    ("Which clause sorts the result set?", "ORDER BY", ["SORT BY", "GROUP BY", "ARRANGE BY"]),
    ("Which statement adds a new column to an existing table?", "ALTER TABLE", ["UPDATE TABLE", "MODIFY TABLE", "CREATE COLUMN"]),
    ("What does NULL represent in SQL?", "A missing or unknown value", ["Zero", "An empty string", "False"]),
    ("Which aggregate function returns the highest value in a column?", "MAX()", ["TOP()", "HIGH()", "UPPER()"]),
    ("Which of these is a DDL command?", "CREATE", ["SELECT", "INSERT", "UPDATE"]),
    ("What is the default sort order of ORDER BY?", "Ascending", ["Descending", "Random", "Insertion order"]),
    ("Which statement removes a table completely, including its structure?", "DROP TABLE", ["DELETE TABLE", "REMOVE TABLE", "TRUNCATE ROW"]),
]
MCQ_Q = [
    ("Which cloud service model provides virtual machines on demand?", "IaaS", ["SaaS", "PaaS", "DaaS"]),
    ("What does HTTP stand for?", "HyperText Transfer Protocol", ["High Transfer Text Protocol", "HyperText Transmission Process", "Host Transfer Technology Protocol"]),
    ("Which AWS service provides object storage?", "Amazon S3", ["Amazon EC2", "Amazon RDS", "AWS Lambda"]),
    ("Which of these is a supervised learning algorithm?", "Linear Regression", ["K-Means", "DBSCAN", "Apriori"]),
    ("What does CSS stand for?", "Cascading Style Sheets", ["Creative Style Syntax", "Computer Style Sheets", "Colorful Style System"]),
    ("Which data structure follows FIFO order?", "Queue", ["Stack", "Tree", "Graph"]),
    ("Which data structure follows LIFO order?", "Stack", ["Queue", "Heap", "Array list"]),
    ("What is the time complexity of binary search?", "O(log n)", ["O(n)", "O(n log n)", "O(1)"]),
    ("Which Git command records staged changes in the local repository?", "git commit", ["git push", "git fetch", "git clone"]),
    ("Which Python library is mainly used for data frames?", "pandas", ["flask", "pygame", "requests"]),
    ("Which chart is best for showing a trend over time?", "Line chart", ["Pie chart", "Scatter map", "Treemap"]),
    ("Which HTTP status code means 'Not Found'?", "404", ["200", "301", "500"]),
    ("Which of these is a NoSQL database?", "MongoDB", ["MySQL", "PostgreSQL", "Oracle"]),
    ("Which metric balances precision and recall?", "F1 score", ["R-squared", "RMSE", "Silhouette score"]),
]


def build_quiz(course_titles_by_cat):
    rows, seen = [], set()

    def add(qtype, q, ans, wrongs, pts, cat):
        if q in seen:
            return False
        seen.add(q)
        course = random.choice(course_titles_by_cat[cat] if cat else sum(course_titles_by_cat.values(), []))
        c = rdt(START + timedelta(days=20), NOW - timedelta(days=10))
        r = blank("quiz")
        r.update(id=uid(), question=q, options=json.dumps(mk_options(ans, wrongs)), quiz_type=qtype,
                 correct_answer=ans, courses=course, isCheckbox="true" if random.random() < 0.05 else "false",
                 points=pts, created_at=c, updated_at=rdt(c, NOW) if random.random() < 0.2 else c)
        rows.append(r)
        return True

    for q, a, w in SQL_Q:
        add("SQL", q, a, w, 1, "Database & SQL")
    for q, a, w in MCQ_Q:
        add("MCQ", q, a, w, 1, None)
    n_apt = (N_QUIZ - len(rows)) * 9 // 19
    n_py = N_QUIZ - len(rows) - n_apt
    tries = 0
    while sum(r["quiz_type"] == "Aptitude" for r in rows) < n_apt and tries < 5000:
        tries += 1
        q, a, w = gen_aptitude()
        add("Aptitude", q, a, w, 2, "Placement Training")
    tries = 0
    while sum(r["quiz_type"] == "Python" for r in rows) < n_py and tries < 5000:
        tries += 1
        q, a, w = gen_python()
        add("Python", q, a, w, 2, "Python Programming")
    random.shuffle(rows)
    TABLES["quiz"] = rows


# --------------------------------------------------------------------------
# Step 2/3 - courses, videos, assets, favourites, batches
# --------------------------------------------------------------------------
LESSON_WORDS = ["Introduction", "Setup and Installation", "Core Concepts", "Hands-on Demo", "Practical Exercise",
                "Common Mistakes", "Best Practices", "Real-world Case Study", "Mini Project", "Revision and Q&A",
                "Advanced Techniques", "Troubleshooting", "Project Walkthrough"]


def build_courses():
    users = TABLES["users"]
    instructors = [u for u in users if u["role"] == "instructor"]
    cats = {c["name"]: c for c in TABLES["categories"]}
    titles = [(cat, t) for cat, ts in CATEGORY_COURSES.items() for t in ts]
    random.shuffle(titles)
    rows, videos, assets = [], [], []
    for idx, (cat, title) in enumerate(titles):
        ins = instructors[idx % len(instructors)]
        is_class = random.random() < 0.4
        dur_label, dur_days = random.choice([("2 Months", 60), ("3 Months", 90), ("4 Months", 120)] if is_class
                                            else [("6 Weeks", 42), ("2 Months", 60), ("3 Months", 90), ("6 Months", 180)])
        latest = (random.choice(range(10000, 40001, 500)) if is_class else random.choice(range(2000, 14001, 500))) - 1
        before = int(latest * random.uniform(1.1, 1.6) // 100 * 100) + 99
        created = rdt(START + timedelta(days=14), START + timedelta(days=150)) if random.random() < 0.8 \
            else rdt(START + timedelta(days=150), NOW - timedelta(days=150))
        created = max(created, ins["created_at"] + timedelta(days=2))
        approved = random.random() < 0.92
        in_home = approved and random.random() < 0.3
        n_vid = random.randint(8, 16)
        c = blank("courses")
        c.update(id=uid(), title=title, slug=slugify(title),
                 short_desc=f"Learn {title} step by step with practical, industry-oriented sessions.",
                 overview=fake.paragraph(nb_sentences=4),
                 latest_price=float(latest), before_price=float(before), lessons=f"{n_vid} Lessons",
                 duration=dur_label, image=f"/uploads/courses/{slugify(title)}.jpg",
                 access_time=random.choices(["Lifetime", "Three Months", "Six Months", "1 Year"], [50, 15, 15, 20])[0],
                 requirements=maybe(0.8, "Basic computer knowledge\nA laptop with internet access"),
                 what_you_will_learn="Core concepts\nHands-on projects\nInterview preparation\nIndustry best practices",
                 who_is_this_course_for=maybe(0.85, "Students, freshers and working professionals who want to upskill"),
                 userId=ins["id"], catId=cats[cat]["id"], approved=approved, in_home_page=in_home,
                 in_home_page_set_at=rdt(created, NOW) if in_home else None, is_class=is_class,
                 created_at=created, updated_at=rdt(created, NOW) if random.random() < 0.5 else created)
        c["_days"] = dur_days
        c["_cat"] = cat
        c["_ins"] = ins
        rows.append(c)

        # videos
        groups = max(2, n_vid // 4)
        for k in range(1, n_vid + 1):
            g = min(groups, (k - 1) * groups // n_vid + 1)
            vc = created + timedelta(days=random.randint(0, 20), hours=random.randint(0, 23))
            v = blank("videos")
            v.update(id=uid(), group_name=f"Module {g}: {random.choice(LESSON_WORDS)}",
                     title=f"{' '.join(title.split()[:2])} - {random.choice(LESSON_WORDS)} ({k})",
                     thumb=f"/uploads/thumbs/{uid()[:8]}.jpg", video=f"/uploads/videos/{uid()[:8]}.mp4",
                     video_length=round(random.uniform(5, 45), 1), is_preview=k <= 2,
                     short_id=k, assets_zip=maybe(0.25, f"/uploads/zips/{uid()[:8]}.zip"),
                     userId=ins["id"], courseId=c["id"], created_at=vc,
                     updated_at=rdt(vc, NOW) if random.random() < 0.3 else vc)
            videos.append(v)
        # assets
        for k in range(1, random.randint(2, 5) + 1):
            ac = created + timedelta(days=random.randint(0, 20))
            a = blank("course_assets")
            a.update(id=uid(), lecture_name=f"Lecture {k} Notes - {title}", lecture_file=f"/uploads/assets/{uid()[:8]}.pdf",
                     courseId=c["id"], created_at=ac, updated_at=ac)
            assets.append(a)
    # instructor subject = category of first course taught
    for ins in instructors:
        mine = [c for c in rows if c["_ins"] is ins]
        ins["instructor_subject"] = mine[0]["_cat"]
    TABLES["courses"], TABLES["videos"], TABLES["course_assets"] = rows, videos, assets


def build_favourites_and_batches():
    students = [u for u in TABLES["users"] if u["role"] == "student"]
    courses = [c for c in TABLES["courses"] if c["approved"]]
    pairs, rows = set(), []
    while len(rows) < 90:
        s, c = random.choice(students), random.choice(courses)
        if (s["id"], c["id"]) in pairs:
            continue
        lo = max(s["created_at"], c["created_at"]) + timedelta(hours=1)
        if lo > NOW - timedelta(days=1):
            continue
        pairs.add((s["id"], c["id"]))
        t = rdt(lo, NOW)
        r = blank("favourites")
        r.update(id=uid(), userId=s["id"], courseId=c["id"], created_at=t, updated_at=t)
        rows.append(r)
    TABLES["favourites"] = rows

    # batches: 1-2 per class course, instructor = course instructor
    rows, seq = [], defaultdict(int)
    for c in TABLES["courses"]:
        if not c["is_class"]:
            continue
        times = [c["created_at"] + timedelta(minutes=random.randint(1, 120))]
        for _ in range(2):
            nxt = times[-1] + timedelta(days=random.randint(120, 250))
            if nxt < NOW - timedelta(days=30) and random.random() < 0.6:
                times.append(nxt)
            else:
                break
        c["_batches"] = []
        for i, t in enumerate(times, 1):
            seq[t.year] += 1
            b = blank("batches")
            upcoming = t > NOW - timedelta(days=45)
            b.update(id=uid(), name=f"{c['title']} - Batch {i}", instructor_id=c["userId"],
                     batchNo=f"B-{t.year}-{seq[t.year]:02d}", isActive=random.random() < 0.75,
                     isUpcoming=1 if upcoming else 0, created_at=t, updated_at=rdt(t, NOW) if random.random() < 0.5 else t)
            rows.append(b)
            c["_batches"].append(b)
    TABLES["batches"] = rows


# --------------------------------------------------------------------------
# Step 4/5/6 - enrolments and everything that hangs off them
# --------------------------------------------------------------------------
def build_enrolments():
    users = {u["id"]: u for u in TABLES["users"]}
    students = [u for u in TABLES["users"] if u["role"] == "student"]
    courses = [c for c in TABLES["courses"] if c["approved"]]
    vids_by_course = defaultdict(list)
    for v in TABLES["videos"]:
        vids_by_course[v["courseId"]].append(v)
    for lst in vids_by_course.values():
        lst.sort(key=lambda v: v["short_id"])
    assets_by_course = defaultdict(list)
    for a in TABLES["course_assets"]:
        assets_by_course[a["courseId"]].append(a["lecture_name"])
    quiz_types = sorted({q["quiz_type"] for q in TABLES["quiz"]})
    task_types = [t["title"] for t in TABLES["task_type"]]
    task_ids = [t["id"] for t in TABLES["tasks"]]

    enrol, inv, txn, prog, cert, rew, used, att, bm, tprog = ([] for _ in range(10))
    pairs, cert_no = set(), 100
    n_enrol, attempts = defaultdict(int), 0

    while len(enrol) < N_ENROLMENTS and attempts < 500000:
        attempts += 1
        start = pick_month_date(1)
        stu_pool = [u for u in students if u["created_at"] <= start - timedelta(days=3)
                    and n_enrol[u["id"]] < MAX_PER_STUDENT]
        crs_pool = [c for c in courses if c["created_at"] <= start - timedelta(days=3)]
        if not stu_pool or not crs_pool:
            continue
        # prefer students with fewer enrolments so most end up with 2-3
        u = random.choices(stu_pool, weights=[1 / (1 + n_enrol[x["id"]]) for x in stu_pool])[0]
        c = random.choice(crs_pool)
        if (u["id"], c["id"]) in pairs:
            continue
        if c["is_class"] and start > NOW - timedelta(days=45):
            continue  # too recent to have 20+ class days of attendance
        pairs.add((u["id"], c["id"]))
        n_enrol[u["id"]] += 1
        end = start + timedelta(days=c["_days"])
        created = start - timedelta(hours=random.randint(0, 24))
        eid = uid()

        # ---- pricing and installments --------------------------------
        price = int(c["latest_price"])
        bought = price if random.random() < 0.7 else int(price * random.choice([0.95, 0.9, 0.85, 0.8, 0.75]))
        n = random.randint(2, 4)
        amts = [bought // n] * n
        amts[-1] += bought - sum(amts)
        dues = [start + timedelta(days=30 * i) for i in range(n)]
        eligible = sum(1 for d in dues if d <= NOW - timedelta(days=1))
        r = random.random()
        k = n if r < 0.6 else (random.randint(1, n - 1) if r < 0.85 else 0)
        k = min(k, eligible)
        method = random.choice(PAY_METHODS)
        if k == 0 and random.random() < 0.5:
            method = None
        txn_mode = {"PhonePe": "UPI"}.get(method, method) or "UPI"
        paid_total = sum(amts[:k])
        invs, last_txn_id, split, events = [], None, [], [created]

        for i in range(n):
            paid = i < k
            iv = blank("payment_invoices")
            pdate = None
            if paid:
                pdate = rdt(dues[i] - timedelta(days=2), dues[i] + timedelta(days=5))
                pdate = min(max(pdate, created), NOW - timedelta(days=1))
            iv.update(id=uid(), userId=u["id"], enrolmentId=eid, amount=amts[i], amount_paid=amts[i] if paid else 0,
                      status="Paid" if paid else ("Overdue" if dues[i] < NOW else "Pending"),
                      title=f"Installment {i + 1}", due_date=dues[i], paid_date=pdate,
                      is_active="1" if i == k else "0", created_at=created, updated_at=pdate or created)
            invs.append(iv)
            if paid:
                events.append(pdate)
                tid = "TXN" + "".join(random.choices("0123456789", k=14))
                last_txn_id = tid
                split.append({"amount": amts[i], "date": pdate.strftime("%Y-%m-%d")})
                if random.random() < 0.06:  # a failed attempt before the successful payment
                    ft = blank("transactions")
                    fc = max(created, pdate - timedelta(hours=random.randint(1, 30)))
                    ft.update(id=uid(), userId=u["id"], enrolmentId=eid, paymentInvoiceId=iv["id"], amount_paid=0,
                              status="Failed", mode=txn_mode, online_transaction_id="TXN" + "".join(random.choices("0123456789", k=14)),
                              payment_name=f"{iv['title']} - {c['title']}", due_date=dues[i], paid_date=None,
                              created_at=fc, updated_at=fc)
                    txn.append(ft)
                t = blank("transactions")
                t.update(id=uid(), userId=u["id"], enrolmentId=eid, paymentInvoiceId=iv["id"], amount_paid=amts[i],
                         status="Success", mode=txn_mode, online_transaction_id=tid,
                         payment_name=f"{iv['title']} - {c['title']}", due_date=dues[i], paid_date=pdate,
                         created_at=pdate, updated_at=pdate)
                txn.append(t)
        inv.extend(invs)

        # ---- progress (only students who paid something) ---------------
        vids = vids_by_course[c["id"]]
        nv, f = len(vids), 0
        if paid_total > 0 and random.random() > 0.12:
            elapsed = max(0.0, min(1.0, (NOW - start) / (end - start)))
            capf = min(1.0, elapsed * 1.15 + 0.05)
            frac = 1.0 if (elapsed >= 0.8 and random.random() < 0.45) else random.random() * capf
            f = round(frac * nv)
        progress = round(f / nv * 100)
        window_end = min(NOW - timedelta(days=1), end)
        span = max(timedelta(days=1), (window_end - start)) * max(0.2, f / nv if nv else 0)
        last_prog = None
        prog_c = c["_cat"]
        qtype_pref = CAT_QUIZ_TYPE.get(prog_c, "MCQ")

        def prog_row(finished, video, qtype, pts, when):
            nonlocal last_prog
            p = blank("course_progresses")
            when = min(when, NOW - timedelta(days=1))
            upd = min(NOW, when + timedelta(minutes=random.randint(0, 2000)))
            p.update(id=uid(), finished=finished, userId=u["id"], courseId=c["id"], enrolmentId=eid,
                     videoId=video, quizType=qtype, points=pts, created_at=when, updated_at=upd)
            prog.append(p)
            events.append(upd)
            last_prog = max(last_prog or upd, upd)

        for i in range(f):
            prog_row(True, vids[i]["id"], None, 10, start + span * (i + 1) / f + timedelta(hours=random.randint(0, 6)))
        if 0 < f < nv and random.random() < 0.6:
            prog_row(False, vids[f]["id"], None, 0, start + span + timedelta(hours=random.randint(1, 12)))
        if f > 0 and f >= nv / 2:
            for _ in range(random.randint(1, 3)):
                qt = qtype_pref if random.random() < 0.7 else random.choice(quiz_types)
                prog_row(random.random() < 0.85, None, qt, random.randint(0, 20),
                         start + span * random.uniform(0.4, 1.0))

        # ---- certificates ----------------------------------------------
        ncert = 0
        if progress == 100 and paid_total == bought and random.random() < 0.9:
            ncert = random.choice([1, 1, 1, 2, 3])
            when = last_prog
            for _ in range(ncert):
                cert_no += 1
                when = min(NOW, when + timedelta(days=random.randint(0, 10), minutes=random.randint(1, 600)))
                cid = f"BRS-{when.year}-{cert_no:06d}"
                ce = blank("certificate_downloads")
                ce.update(id=uid(), enrolmentId=eid, certificateId=cid,
                          certificatePdfUrl=f"https://example.com/certificates/{cid}.pdf", createdAt=when, updatedAt=when)
                cert.append(ce)
                events.append(when)

        # ---- reward points ---------------------------------------------
        if paid_total > 0 and random.random() < 0.55:
            pts = random.choice(range(50, 501, 50))
            rc = created + timedelta(hours=random.randint(1, 72))
            exp = rc + timedelta(days=random.randint(180, 540))
            used_pts = 0
            if random.random() < 0.2:
                uc = rc + timedelta(days=random.randint(1, 60))
                if uc < min(exp, NOW):
                    used_pts = random.choice(range(10, pts + 1, 10))
                    ur = blank("used_reward_points")
                    ur.update(id=uid(), enrolmentId=eid, userId=u["id"], points=used_pts, status=0,
                              created_at=uc, updated_at=uc)
                    used.append(ur)
            rw = blank("reward_points")
            rw.update(id=uid(), enrolmentId=eid, userId=u["id"], points=pts,
                      status=1 if (exp < NOW or used_pts == pts) else 0, expired_on=exp,
                      created_at=rc, updated_at=rdt(rc, NOW) if used_pts else rc)
            rew.append(rw)

        # ---- class-only: attendance and batch -----------------------------
        if c["is_class"] and paid_total > 0:
            b_ok = [b for b in c.get("_batches", []) if b["created_at"] <= created]
            if b_ok:
                b = random.choice(b_ok)
                m = blank("batch_members")
                m.update(id=uid(), batchId=b["id"], enrolmentId=eid, created_at=created, updated_at=created)
                bm.append(m)
            days, d = [], start.replace(hour=0, minute=0, second=0)
            while d <= min(end, NOW - timedelta(days=1)):
                if d.weekday() < 5:
                    days.append(d)
                d += timedelta(days=1)
            days = sorted(random.sample(days, min(len(days), random.randint(20, 60))))
            p_present = random.uniform(0.6, 0.95)
            for d in days:
                st = random.choices(["present", "late", "absent"],
                                    [p_present, (1 - p_present) * 0.4, (1 - p_present) * 0.6])[0]
                ct = d + timedelta(hours=10, minutes=random.randint(0, 45))
                a = blank("attendance_records")
                a.update(id=uid(), enrolmentId=eid, userId=u["id"], attendance_date=d, status=st,
                         created_at=ct, updated_at=ct)
                att.append(a)

        # ---- tasks -----------------------------------------------------------
        if progress >= 30:
            for _ in range(random.randint(1, 3)):
                ttype = random.choice(task_types)
                ts = rdt(start + timedelta(days=1), max(start + timedelta(days=2), min(NOW - timedelta(days=2), end)))
                st = random.choices(["Completed", "Submitted", "Pending"], [55, 30, 15])[0]
                te = ts + timedelta(days=random.randint(1, 10)) if st != "Pending" or random.random() < 0.5 else None
                if te:
                    te = min(te, NOW)
                    te = max(te, ts)
                tp = blank("task_progress")
                tp.update(id=uid(), task_name=f"{ttype}: {c['title']}", task_file=maybe(0.8, f"/uploads/tasks/{uid()[:8]}.zip"),
                          task_type=ttype, userId=u["id"], courseId=c["id"], taskId=random.choice(task_ids),
                          status=st, duration=None if st == "Pending" else random.randint(30, 480),
                          start_date=ts, end_date=te, created_at=ts, updated_at=te or ts)
                tprog.append(tp)

        # ---- the enrolment row itself ----------------------------------------
        e = blank("enrolments")
        e.update(id=eid, bought_price=float(bought), payment_method=method, buyer_name=f"{u['first_name']} {u['last_name']}",
                 buyer_email=u["email"], buyer_avatar=u["profile_photo"],
                 types="offline" if (c["is_class"] and random.random() < 0.65) else "online",
                 userId=u["id"], courseId=c["id"], start_date=start, end_date=end, amount_paid=paid_total,
                 balance_amount=bought - paid_total, status="paid" if bought - paid_total == 0 else "unpaid",
                 progress_status=progress, certificate_downloads=ncert, enrolment_title=c["title"],
                 enrolment_duration=c["duration"], payment_split=json.dumps(split),
                 phonepe_order_id=("OD" + "".join(random.choices("0123456789", k=16))) if (method == "PhonePe" and paid_total) else None,
                 txn_id=last_txn_id, college_name=u["college_name"], deg_dept=u["deg_dept"], reg_num=u["reg_num"],
                 assigned_study_materials=json.dumps(random.sample(assets_by_course[c["id"]], random.randint(1, 2)))
                 if random.random() < 0.4 else "[]",
                 created_at=created, updated_at=max(events))
        enrol.append(e)

    for name, rows in [("enrolments", enrol), ("payment_invoices", inv), ("transactions", txn),
                       ("course_progresses", prog), ("certificate_downloads", cert), ("reward_points", rew),
                       ("used_reward_points", used), ("attendance_records", att), ("batch_members", bm),
                       ("task_progress", tprog)]:
        TABLES[name] = rows


def build_instructor_earnings():
    """monthly payout per course = instructor share of the invoices paid that month"""
    course = {c["id"]: c for c in TABLES["courses"]}
    enrol_course = {e["id"]: e["courseId"] for e in TABLES["enrolments"]}
    share = {c["userId"]: random.choice([0.55, 0.6, 0.65, 0.7]) for c in TABLES["courses"]}
    bucket = defaultdict(int)
    for iv in TABLES["payment_invoices"]:
        if iv["paid_date"]:
            m = iv["paid_date"].replace(day=1, hour=0, minute=0, second=0)
            bucket[(enrol_course[iv["enrolmentId"]], m)] += iv["amount_paid"]
    rows = []
    for (cid, m), total in sorted(bucket.items(), key=lambda x: (x[0][1], x[0][0])):
        c = course[cid]
        created = min(NOW, add_months(m, 1) + timedelta(days=random.randint(1, 5), hours=random.randint(9, 18)))
        age = (NOW - add_months(m, 1)).days
        status = random.choices(["paid", "cancelled", "due"], [92, 3, 5])[0] if age > 45 else "due"
        r = blank("instructor_earnings")
        r.update(id=uid(), earnings=round(total * share[c["userId"]], 2), userId=c["userId"], courseId=cid,
                 status=status, created_at=created,
                 updated_at=min(NOW, created + timedelta(days=random.randint(3, 20))) if status != "due" else created)
        rows.append(r)
    TABLES["instructor_earnings"] = rows


TITLES = ["Live class", "Doubt clearing session", "Assignment review", "Mentoring session", "Mock interview",
          "Project review", "Revision class", "Hands-on lab"]
SUMMARIES = ["Covered the planned topics and solved student doubts.", "Reviewed submissions and shared feedback.",
             "Walked through a hands-on exercise.", "Discussed project progress and next steps.",
             "Conducted mock interviews for the batch.", "Revised the previous module with practice questions."]


def build_work_sessions():
    rows = []
    for ins in [u for u in TABLES["users"] if u["role"] == "instructor"]:
        m = ins["created_at"].replace(day=1, hour=0, minute=0, second=0)
        m = add_months(m, 0)
        while m <= NOW:
            last = min(add_months(m, 1) - timedelta(days=1), NOW - timedelta(days=1))
            days, d = [], max(m, ins["created_at"] + timedelta(days=3))
            d = d.replace(hour=0, minute=0, second=0)
            while d <= last:
                if d.weekday() < 5:
                    days.append(d)
                d += timedelta(days=1)
            if days:
                want = random.randint(20, 25)
                if last.month == NOW.month and last.year == NOW.year:  # partial current month
                    want = max(1, round(want * len(days) / 22))
                pool = sorted(days * 2)
                chosen = sorted(random.sample(pool, min(want, len(pool))))
                by_day = defaultdict(int)
                for d in chosen:
                    by_day[d] += 1
                for d, cnt in by_day.items():
                    cur = d + timedelta(hours=random.choice([9, 10, 11, 14]), minutes=random.choice([0, 15, 30, 45]))
                    for _ in range(cnt):
                        dur = timedelta(minutes=random.choice(range(60, 181, 15)))
                        s, e = cur, cur + dur
                        if e.hour >= 20 or e.date() != s.date():
                            break
                        ctime = min(NOW, e + timedelta(minutes=random.randint(0, 60)))
                        edited = random.random() < 0.08
                        w = blank("work_sessions")
                        w.update(id=uid(), userId=ins["id"], date=d.strftime("%Y-%m-%d"),
                                 start_time=s.strftime("%H:%M:%S"), end_time=e.strftime("%H:%M:%S"),
                                 session_title=random.choice(TITLES), summary=maybe(0.85, random.choice(SUMMARIES)),
                                 session_timing=str(dur).rjust(8, "0"),
                                 session_status=random.choices([0, 1], [25, 75])[0], status=random.choices([0, 1], [20, 80])[0],
                                 edit_description="Corrected the session timing." if edited else None,
                                 is_edited=1 if edited else 0, is_requested=1 if random.random() < 0.05 else 0,
                                 created_at=ctime, updated_at=min(NOW, ctime + timedelta(hours=random.randint(1, 30))) if edited else ctime)
                        rows.append(w)
                        cur = e + timedelta(minutes=random.randint(30, 60))
            m = add_months(m, 1)
    TABLES["work_sessions"] = rows


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="brassy_data")
    args = ap.parse_args()
    random.seed(args.seed)
    Faker.seed(args.seed)

    build_users()
    build_simple_tables()
    build_courses()
    by_cat = defaultdict(list)
    for c in TABLES["courses"]:
        by_cat[c["_cat"]].append(c["title"])
    build_quiz(by_cat)
    build_favourites_and_batches()
    build_enrolments()
    build_instructor_earnings()
    build_work_sessions()

    os.makedirs(args.out, exist_ok=True)
    lines = ["# Brassy LMS dummy dataset", "",
             f"Generated with Python + Faker (`generate_data.py`, seed {args.seed}) on {NOW:%Y-%m-%d}.", "",
             "| Table | Rows |", "|---|---|"]
    for t in ORDER:
        write_csv(args.out, t)
        lines.append(f"| {t} | {len(TABLES[t])} |")
        print(f"{t:24s}{len(TABLES[t]):>7d}")
    with open(os.path.join(args.out, "README.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nCSV files written to ./{args.out}/")


if __name__ == "__main__":
    main()
