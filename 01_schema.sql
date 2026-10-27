-- Brassy LMS dummy database schema (MySQL 8 / MariaDB)
DROP DATABASE IF EXISTS brassy_lms;
CREATE DATABASE brassy_lms CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE brassy_lms;

SET FOREIGN_KEY_CHECKS = 0;

-- ---------- Step 1: standalone / parent tables ----------
CREATE TABLE users (
  id CHAR(36) PRIMARY KEY,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  gender VARCHAR(20),
  designation VARCHAR(150),
  bio TEXT,
  profile_photo VARCHAR(255),
  location VARCHAR(150),
  phone VARCHAR(20),
  reset_password_token CHAR(36),
  reset_password_send_at DATETIME,
  reset_password_expires DATETIME,
  reset_password_at DATETIME,
  website VARCHAR(255),
  twitter VARCHAR(255),
  facebook VARCHAR(255),
  linkedin VARCHAR(255),
  youtube VARCHAR(255),
  role ENUM('student','admin','instructor') NOT NULL DEFAULT 'student',
  email_confirmed BOOLEAN DEFAULT FALSE,
  email_confirmed_at DATETIME,
  instructor_request BOOLEAN DEFAULT FALSE,
  instructor_request_confirmed BOOLEAN DEFAULT FALSE,
  instructor_request_confirmed_at DATETIME,
  instructor_status BOOLEAN DEFAULT FALSE,
  instructor_subject VARCHAR(255),
  instructor_description VARCHAR(500),
  status BOOLEAN DEFAULT TRUE,
  is_profile_public BOOLEAN DEFAULT TRUE,
  college_name VARCHAR(255),
  deg_dept VARCHAR(100),
  reg_num VARCHAR(50),
  year_of_graduation INT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE categories (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(150),
  slug VARCHAR(150) UNIQUE,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE task_type (
  id CHAR(36) PRIMARY KEY,
  title VARCHAR(150),
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE quiz (
  id CHAR(36) PRIMARY KEY,
  question VARCHAR(1000) NOT NULL,
  options VARCHAR(1000) NOT NULL,
  quiz_type VARCHAR(100) NOT NULL,
  correct_answer VARCHAR(500) NOT NULL,
  courses VARCHAR(255) NOT NULL,
  isCheckbox ENUM('true','false') NOT NULL,
  points INT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE coupons (
  id CHAR(36) PRIMARY KEY,
  code VARCHAR(50),
  discount FLOAT,
  exp_date DATETIME,
  status BOOLEAN,
  deleted_at DATETIME,
  active_for_full_site BOOLEAN,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE partners (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(150),
  partner_image VARCHAR(255),
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE subscriptions (
  id CHAR(36) PRIMARY KEY,
  email VARCHAR(255),
  active BOOLEAN,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE testimonials (
  id CHAR(36) PRIMARY KEY,
  image_url VARCHAR(255),
  name VARCHAR(150),
  designation VARCHAR(150),
  description TEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE enquiries (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  email VARCHAR(255),
  phone VARCHAR(20) NOT NULL,
  college_name VARCHAR(255),
  location VARCHAR(150),
  mode ENUM('online','offline'),
  message VARCHAR(500),
  domain VARCHAR(150),
  date_of_joining DATETIME,
  enquiry_type VARCHAR(100),
  duration VARCHAR(50),
  education_status VARCHAR(100),
  slot VARCHAR(50),
  batch_startdate VARCHAR(50),
  register_num VARCHAR(50),
  deg_dept VARCHAR(100),
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE company_enquire (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  phone_no VARCHAR(20) NOT NULL,
  email_id VARCHAR(255),
  company VARCHAR(255),
  job_description VARCHAR(500),
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

-- ---------- Step 2: courses ----------
CREATE TABLE courses (
  id CHAR(36) PRIMARY KEY,
  title VARCHAR(255),
  slug VARCHAR(255),
  short_desc TEXT,
  overview TEXT,
  latest_price FLOAT,
  before_price FLOAT,
  lessons VARCHAR(50),
  duration VARCHAR(50),
  image VARCHAR(255),
  access_time ENUM('Lifetime','Three Months','Six Months','1 Year') DEFAULT 'Lifetime',
  requirements TEXT,
  what_you_will_learn TEXT,
  who_is_this_course_for TEXT,
  userId CHAR(36) NOT NULL,
  catId CHAR(36) NOT NULL,
  approved BOOLEAN,
  in_home_page BOOLEAN,
  in_home_page_set_at DATETIME,
  is_class BOOLEAN,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (catId) REFERENCES categories(id)
);

-- ---------- Step 3 ----------
CREATE TABLE videos (
  id CHAR(36) PRIMARY KEY,
  group_name VARCHAR(255),
  title VARCHAR(255),
  thumb VARCHAR(255),
  video VARCHAR(255),
  video_length FLOAT,
  is_preview BOOLEAN,
  short_id INT,
  assets_zip VARCHAR(255),
  userId CHAR(36) NOT NULL,
  courseId CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (courseId) REFERENCES courses(id)
);

CREATE TABLE course_assets (
  id CHAR(36) PRIMARY KEY,
  lecture_name VARCHAR(255),
  lecture_file VARCHAR(255),
  courseId CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (courseId) REFERENCES courses(id)
);

CREATE TABLE favourites (
  id CHAR(36) PRIMARY KEY,
  userId CHAR(36) NOT NULL,
  courseId CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_fav (userId, courseId),
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (courseId) REFERENCES courses(id)
);

-- Field list for tasks is still pending in the guide (course_task.js missing)
CREATE TABLE tasks (
  id CHAR(36) PRIMARY KEY,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE batches (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  instructor_id CHAR(36),            -- logical link only, no FK constraint
  batchNo VARCHAR(50) NOT NULL,
  isActive BOOLEAN DEFAULT TRUE,
  isUpcoming INT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE instructor_earnings (
  id CHAR(36) PRIMARY KEY,
  earnings FLOAT,
  userId CHAR(36) NOT NULL,
  courseId CHAR(36) NOT NULL,
  status ENUM('due','paid','cancelled') DEFAULT 'due',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (courseId) REFERENCES courses(id)
);

CREATE TABLE work_sessions (
  id CHAR(36) PRIMARY KEY,
  userId CHAR(36) NOT NULL,
  `date` DATE NOT NULL,
  start_time TIME,
  end_time TIME,
  session_title VARCHAR(255),
  summary TEXT,
  session_timing TIME,
  session_status INT DEFAULT 0,
  status INT DEFAULT 0,
  edit_description TEXT,
  is_edited TINYINT DEFAULT 0,
  is_requested TINYINT DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id)
);

-- ---------- Step 4 ----------
CREATE TABLE enrolments (
  id CHAR(36) PRIMARY KEY,
  bought_price FLOAT,
  payment_method VARCHAR(50),
  buyer_name VARCHAR(255),
  buyer_email VARCHAR(255),
  buyer_avatar VARCHAR(255),
  types VARCHAR(50),
  userId CHAR(36) NOT NULL,
  courseId CHAR(36) NOT NULL,
  start_date DATETIME NOT NULL,
  end_date DATETIME NOT NULL,
  amount_paid INT,
  balance_amount INT,
  status ENUM('paid','unpaid'),
  progress_status INT,
  certificate_downloads INT,
  enrolment_title VARCHAR(255),
  enrolment_duration VARCHAR(50),
  payment_split VARCHAR(255) DEFAULT '[]',
  phonepe_order_id VARCHAR(255),
  txn_id VARCHAR(255),
  college_name VARCHAR(255),
  deg_dept VARCHAR(100),
  reg_num VARCHAR(50),
  assigned_study_materials TEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (courseId) REFERENCES courses(id)
);

-- ---------- Step 5 ----------
CREATE TABLE payment_invoices (
  id CHAR(36) PRIMARY KEY,
  userId CHAR(36) NOT NULL,
  enrolmentId CHAR(36) NOT NULL,
  amount_paid INT,
  amount INT,
  status VARCHAR(30),
  title VARCHAR(100),
  due_date DATETIME,
  paid_date DATETIME,
  is_active ENUM('0','1') DEFAULT '0',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (enrolmentId) REFERENCES enrolments(id)
);

CREATE TABLE reward_points (
  id CHAR(36) PRIMARY KEY,
  enrolmentId CHAR(36) NOT NULL UNIQUE,
  userId CHAR(36) NOT NULL,
  points INT,
  status INT DEFAULT 0,
  expired_on DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (enrolmentId) REFERENCES enrolments(id)
);

CREATE TABLE used_reward_points (
  id CHAR(36) PRIMARY KEY,
  enrolmentId CHAR(36) NOT NULL UNIQUE,
  userId CHAR(36) NOT NULL,
  points INT,
  status INT DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (enrolmentId) REFERENCES enrolments(id)
);

CREATE TABLE attendance_records (
  id CHAR(36) PRIMARY KEY,
  enrolmentId CHAR(36) NOT NULL,
  userId CHAR(36) NOT NULL,
  attendance_date DATETIME NOT NULL,
  status ENUM('present','absent','late') NOT NULL DEFAULT 'present',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_att (enrolmentId, attendance_date),
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (enrolmentId) REFERENCES enrolments(id)
);

CREATE TABLE batch_members (
  id CHAR(36) PRIMARY KEY,
  batchId CHAR(36) NOT NULL,
  enrolmentId CHAR(36) NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (batchId) REFERENCES batches(id),
  FOREIGN KEY (enrolmentId) REFERENCES enrolments(id)
);

CREATE TABLE certificate_downloads (
  id CHAR(36) PRIMARY KEY,
  enrolmentId CHAR(36) NOT NULL,
  certificateId VARCHAR(50) NOT NULL,
  certificatePdfUrl VARCHAR(255) NOT NULL,
  createdAt DATETIME NOT NULL,
  updatedAt DATETIME NOT NULL,
  FOREIGN KEY (enrolmentId) REFERENCES enrolments(id)
);

CREATE TABLE course_progresses (
  id CHAR(36) PRIMARY KEY,
  finished BOOLEAN,
  userId CHAR(36) NOT NULL,
  courseId CHAR(36) NOT NULL,
  enrolmentId CHAR(36) NOT NULL,
  videoId CHAR(36),
  quizType VARCHAR(100),
  points INT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (courseId) REFERENCES courses(id),
  FOREIGN KEY (enrolmentId) REFERENCES enrolments(id),
  FOREIGN KEY (videoId) REFERENCES videos(id)
);

CREATE TABLE task_progress (
  id CHAR(36) PRIMARY KEY,
  task_name VARCHAR(255),
  task_file VARCHAR(255),
  task_type VARCHAR(100),
  userId CHAR(36) NOT NULL,
  courseId CHAR(36) NOT NULL,
  taskId CHAR(36) NOT NULL,
  status VARCHAR(30),
  duration INT,
  start_date DATETIME,
  end_date DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (courseId) REFERENCES courses(id),
  FOREIGN KEY (taskId) REFERENCES tasks(id)
);

-- ---------- Step 6 ----------
CREATE TABLE transactions (
  id CHAR(36) PRIMARY KEY,
  userId CHAR(36) NOT NULL,
  enrolmentId CHAR(36) NOT NULL,
  paymentInvoiceId CHAR(36) NOT NULL,
  amount_paid INT,
  status VARCHAR(30),
  mode VARCHAR(30),
  online_transaction_id VARCHAR(100),
  payment_name VARCHAR(150),
  due_date DATETIME,
  paid_date DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (userId) REFERENCES users(id),
  FOREIGN KEY (enrolmentId) REFERENCES enrolments(id),
  FOREIGN KEY (paymentInvoiceId) REFERENCES payment_invoices(id)
);

SET FOREIGN_KEY_CHECKS = 1;
