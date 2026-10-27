#!/usr/bin/env python3
"""
Load the generated CSVs into the brassy_lms database (create it first with 01_schema.sql).

    pip install pymysql
    python load_to_mysql.py --user root --password YOUR_PASSWORD
    python load_to_mysql.py --user root --password YOUR_PASSWORD --host 127.0.0.1 --port 3306 --folder brassy_data
"""
import argparse
import csv
import os

import pymysql

# parents-first table order (so foreign keys are always valid)
ORDER = ["users", "categories", "task_type", "quiz", "coupons", "partners", "subscriptions", "testimonials",
         "enquiries", "company_enquire", "courses", "videos", "course_assets", "favourites", "tasks", "batches",
         "instructor_earnings", "work_sessions", "enrolments", "payment_invoices", "reward_points",
         "used_reward_points", "attendance_records", "batch_members", "certificate_downloads",
         "course_progresses", "task_progress", "transactions"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", default="root")
    ap.add_argument("--password", default="")
    ap.add_argument("--database", default="brassy_lms")
    ap.add_argument("--folder", default="brassy_data")
    a = ap.parse_args()

    conn = pymysql.connect(host=a.host, port=a.port, user=a.user, password=a.password,
                           database=a.database, charset="utf8mb4", autocommit=False)
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in reversed(ORDER):          # clear children first so the script can be re-run
        cur.execute(f"DELETE FROM `{table}`")
    for table in ORDER:
        with open(os.path.join(a.folder, table + ".csv"), newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = [[(v if v != "" else None) for v in r] for r in reader]   # empty -> NULL
        cols = ", ".join(f"`{c}`" for c in header)
        sql = f"INSERT INTO `{table}` ({cols}) VALUES ({', '.join(['%s'] * len(header))})"
        for i in range(0, len(rows), 2000):
            cur.executemany(sql, rows[i:i + 2000])
        conn.commit()
        print(f"{table:24s}{len(rows):>7d} rows loaded")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
