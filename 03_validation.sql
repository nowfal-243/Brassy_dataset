-- Brassy LMS - business-rule checks (Section 6 + checklist in Section 9)
-- Every row returned should show violations = 0
USE brassy_lms;

SELECT '1. courses.userId is an instructor' AS check_name, COUNT(*) AS violations
FROM courses c JOIN users u ON u.id = c.userId WHERE u.role <> 'instructor'
UNION ALL SELECT '2. videos.userId is the course instructor', COUNT(*)
FROM videos v JOIN courses c ON c.id = v.courseId WHERE v.userId <> c.userId
UNION ALL SELECT '3. instructor_earnings.userId is an instructor', COUNT(*)
FROM instructor_earnings e JOIN users u ON u.id = e.userId WHERE u.role <> 'instructor'
UNION ALL SELECT '4. work_sessions.userId is an instructor', COUNT(*)
FROM work_sessions w JOIN users u ON u.id = w.userId WHERE u.role <> 'instructor'
UNION ALL SELECT '5. batches.instructor_id is an instructor', COUNT(*)
FROM batches b LEFT JOIN users u ON u.id = b.instructor_id WHERE u.id IS NULL OR u.role <> 'instructor'
UNION ALL SELECT '6. enrolments/favourites/attendance userId is a student', (
  (SELECT COUNT(*) FROM enrolments e JOIN users u ON u.id = e.userId WHERE u.role <> 'student') +
  (SELECT COUNT(*) FROM favourites e JOIN users u ON u.id = e.userId WHERE u.role <> 'student') +
  (SELECT COUNT(*) FROM attendance_records e JOIN users u ON u.id = e.userId WHERE u.role <> 'student'))
UNION ALL SELECT '7. enrolments end_date > start_date', COUNT(*) FROM enrolments WHERE end_date <= start_date
UNION ALL SELECT '8. enrolments balance = bought - paid', COUNT(*) FROM enrolments WHERE balance_amount <> bought_price - amount_paid
UNION ALL SELECT '9. status = paid only when balance = 0', COUNT(*) FROM enrolments
  WHERE (status = 'paid' AND balance_amount <> 0) OR (status = 'unpaid' AND balance_amount = 0)
UNION ALL SELECT '10. enrolments.amount_paid = sum of successful transactions', COUNT(*)
FROM enrolments e LEFT JOIN (SELECT enrolmentId, SUM(amount_paid) s FROM transactions WHERE status = 'Success' GROUP BY enrolmentId) t
  ON t.enrolmentId = e.id WHERE e.amount_paid <> COALESCE(t.s, 0)
UNION ALL SELECT '11. transaction invoice has same enrolment and user', COUNT(*)
FROM transactions t JOIN payment_invoices i ON i.id = t.paymentInvoiceId
WHERE t.enrolmentId <> i.enrolmentId OR t.userId <> i.userId
UNION ALL SELECT '12. paid_date only on paid invoices', COUNT(*) FROM payment_invoices
  WHERE (status = 'Paid') <> (paid_date IS NOT NULL)
UNION ALL SELECT '13. paid invoice paid_date within -3..+6 days of due_date', COUNT(*) FROM payment_invoices
  WHERE paid_date IS NOT NULL AND (paid_date < due_date - INTERVAL 3 DAY OR paid_date > due_date + INTERVAL 6 DAY)
       AND paid_date > created_at
UNION ALL SELECT '14. child rows: userId owns the enrolment (+courseId matches)', (
  (SELECT COUNT(*) FROM course_progresses x JOIN enrolments e ON e.id = x.enrolmentId WHERE x.userId <> e.userId OR x.courseId <> e.courseId) +
  (SELECT COUNT(*) FROM payment_invoices x JOIN enrolments e ON e.id = x.enrolmentId WHERE x.userId <> e.userId) +
  (SELECT COUNT(*) FROM transactions x JOIN enrolments e ON e.id = x.enrolmentId WHERE x.userId <> e.userId) +
  (SELECT COUNT(*) FROM reward_points x JOIN enrolments e ON e.id = x.enrolmentId WHERE x.userId <> e.userId) +
  (SELECT COUNT(*) FROM used_reward_points x JOIN enrolments e ON e.id = x.enrolmentId WHERE x.userId <> e.userId) +
  (SELECT COUNT(*) FROM attendance_records x JOIN enrolments e ON e.id = x.enrolmentId WHERE x.userId <> e.userId))
UNION ALL SELECT '15. attendance/batch_members only for is_class courses', (
  (SELECT COUNT(*) FROM attendance_records a JOIN enrolments e ON e.id = a.enrolmentId JOIN courses c ON c.id = e.courseId WHERE c.is_class = 0) +
  (SELECT COUNT(*) FROM batch_members a JOIN enrolments e ON e.id = a.enrolmentId JOIN courses c ON c.id = e.courseId WHERE c.is_class = 0))
UNION ALL SELECT '16. certificates only for progress_status = 100', COUNT(*)
FROM certificate_downloads c JOIN enrolments e ON e.id = c.enrolmentId WHERE e.progress_status <> 100
UNION ALL SELECT '17. enrolments.certificate_downloads = rows in table', COUNT(*)
FROM enrolments e LEFT JOIN (SELECT enrolmentId, COUNT(*) n FROM certificate_downloads GROUP BY enrolmentId) c
  ON c.enrolmentId = e.id WHERE e.certificate_downloads <> COALESCE(c.n, 0)
UNION ALL SELECT '18. used points <= earned points', COUNT(*)
FROM used_reward_points u LEFT JOIN reward_points r ON r.enrolmentId = u.enrolmentId WHERE r.id IS NULL OR u.points > r.points
UNION ALL SELECT '19. updated_at >= created_at (all tables)', (
  (SELECT COUNT(*) FROM users WHERE updated_at < created_at) + (SELECT COUNT(*) FROM courses WHERE updated_at < created_at) +
  (SELECT COUNT(*) FROM videos WHERE updated_at < created_at) + (SELECT COUNT(*) FROM enrolments WHERE updated_at < created_at) +
  (SELECT COUNT(*) FROM payment_invoices WHERE updated_at < created_at) + (SELECT COUNT(*) FROM transactions WHERE updated_at < created_at) +
  (SELECT COUNT(*) FROM course_progresses WHERE updated_at < created_at) + (SELECT COUNT(*) FROM task_progress WHERE updated_at < created_at) +
  (SELECT COUNT(*) FROM attendance_records WHERE updated_at < created_at) + (SELECT COUNT(*) FROM work_sessions WHERE updated_at < created_at) +
  (SELECT COUNT(*) FROM batches WHERE updated_at < created_at) + (SELECT COUNT(*) FROM reward_points WHERE updated_at < created_at) +
  (SELECT COUNT(*) FROM instructor_earnings WHERE updated_at < created_at) + (SELECT COUNT(*) FROM certificate_downloads WHERE updatedAt < createdAt))
UNION ALL SELECT '20. work_sessions end_time > start_time', COUNT(*) FROM work_sessions WHERE end_time <= start_time
UNION ALL SELECT '21. overlapping work_sessions (same instructor/date)', COUNT(*)
FROM work_sessions a JOIN work_sessions b ON a.userId = b.userId AND a.`date` = b.`date` AND a.id < b.id
WHERE a.start_time < b.end_time AND b.start_time < a.end_time
UNION ALL SELECT '22. quiz.correct_answer is one of the options', COUNT(*)
FROM quiz WHERE JSON_SEARCH(options, 'one', correct_answer) IS NULL
UNION ALL SELECT '23. task_progress end_date >= start_date', COUNT(*) FROM task_progress WHERE end_date < start_date
UNION ALL SELECT '24. courses before_price >= latest_price', COUNT(*) FROM courses WHERE before_price < latest_price;

-- Approximate row counts (InnoDB estimates; the exact counts are in brassy_data/README.md)
SELECT table_name, table_rows FROM information_schema.tables
WHERE table_schema = 'brassy_lms' ORDER BY table_name;
