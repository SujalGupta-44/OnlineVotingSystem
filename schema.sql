-- schema.sql
CREATE DATABASE IF NOT EXISTS VotingSystem_db;
USE VotingSystem_db;

-- Users Table (Voters) — matches registration.html fields (aadhar used as key)
CREATE TABLE IF NOT EXISTS users (
  aadhar_no VARCHAR(12) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  father_name VARCHAR(100),
  age INT,
  city VARCHAR(100),
  password VARCHAR(255) NOT NULL
);

-- Admins Table
CREATE TABLE IF NOT EXISTS admins (
  admin_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL
);

-- Elections Table (matches add_election.html + app.py usage)
CREATE TABLE IF NOT EXISTS elections (
  election_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(150) NOT NULL,
  description TEXT,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status ENUM('UPCOMING','ACTIVE','CLOSED') DEFAULT 'UPCOMING'
);

-- Candidates Table (matches add_candidate.html)
CREATE TABLE IF NOT EXISTS candidates (
  candidate_id INT AUTO_INCREMENT PRIMARY KEY,
  election_id INT NOT NULL,
  name VARCHAR(100) NOT NULL,
  party VARCHAR(100),
  FOREIGN KEY (election_id) REFERENCES elections(election_id) ON DELETE CASCADE
);

-- Votes Table (stores each vote; prevents double-vote per user per election)
CREATE TABLE IF NOT EXISTS votes (
  vote_id INT AUTO_INCREMENT PRIMARY KEY,
  aadhar_no VARCHAR(12) NOT NULL,
  election_id INT NOT NULL,
  candidate_id INT NOT NULL,
  voted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (aadhar_no) REFERENCES users(aadhar_no) ON DELETE CASCADE,
  FOREIGN KEY (election_id) REFERENCES elections(election_id) ON DELETE CASCADE,
  FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
  UNIQUE KEY uniq_vote (aadhar_no, election_id)
);
