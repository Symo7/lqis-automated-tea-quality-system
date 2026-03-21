# Product Requirements Document (PRD)
**Project Name**: LQIS (Leaf Quality Inspection System) Automated Tea Quality System  
**Document Version**: 1.0  
**Target Platform**: Responsive Web Application (Mobile-first for Inspectors, Desktop-optimized for Supervisors/Admins)  

---

## 1. Product Overview
### 1.1 Objective
The purpose of the LQIS system is to automate, standardize, and accelerate the quality control process of raw tea leaves at the factory intake stage. It replaces manual, paper-based scoring with a digital platform that leverages AI-assisted image prediction, threshold-based dynamic scoring, and offline-capable mobile forms.

### 1.2 Target Audience
- **Inspectors (Field Operators)**: Personnel at the factory intake who physically sample the incoming tea batches, take photos, and log base metrics (Moisture %, Foreign Matter %).
- **Supervisors (Quality Managers)**: Managerial staff who review the aggregated batch data, evaluate the system-calculated Quality Score against standard thresholds, and make conclusive Accept/Reject decisions.
- **System Administrators**: Technical or Operations leads responsible for managing master data (Factories, Buying Centers, Suppliers, Batches, and Quality Thresholds).

---

## 2. Core Features & Requirements

### 2.1 Role-Based Access Control (RBAC) & Navigation
- **Authentication**: secure Login/Logout flows via Django built-in auth.
- **Dynamic Routing**: 
  - Inspectors default to the immediate "Factory Intake Sampling" workflow.
  - Supervisors default to the aggregated "Supervisor Dashboard".
  - Admins retain access to all workflows including "Master Data" management.

### 2.2 Offline-First Progressive Web App (PWA)
- **Service Worker & Manifest**: The app must be installable as a PWA on mobile devices.
- **Offline Sync Queue**: Inspectors frequently operate in low-connectivity areas. Submission forms must queue payload data alongside locally encrypted/cached images when offline, actively attempting background transmission when a network is restored.

### 2.3 Factory Intake Workflow (Inspector UX)
- **Live Form Filtering**: Cascading auto-filtering for `Factory → Tea Buying Center → Supplier → Batch`.
- **Hardware Integration**: The image upload field (`accept="image/*;capture=camera"`) must natively trigger the mobile phone's camera.
- **Predictive Modeling**: Incorporates an `ai_engine` capable of receiving a leafy image and returning a "Predicted Pluck Class" and "Predicted Score" along with confidence margins.
- **Dynamic Scoring Previews**: Live client-side Javascript estimators calculating the final `Quality Score` based on moisture & foreign-matter percentages.

### 2.4 Supervisor Dashboard & Decision Engine
- **Decision Workflow**: Supervisors require a structured, queue-based view of all "Undecided" batches allowing them to step sequentially from one batch to the "Next Pending Batch".
- **Real-Time Data Aggregations**: Chart.js powered visual trends mapping 7-Day Performance, Quality Distributions, Alert anomalies, and Supplier Comparison tracking.
- **Alert Generation**: Samples breaching configured [FactoryThreshold](file:///c:/Users/marii/lqis-automated-tea-quality-system/lqis_project/core/models.py#72-80) markers automatically spawn `Quality Alerts` routed instantly to the Dashboard.

### 2.5 Reporting & Communications
- **Daily Extracts**: Date-filtered reports capable of cleanly exporting flat data into CSV, XLSX, and PDF formats for compliance trails.
- **Automated Summary Delivery**: A Cron-scheduled Django management command (`send_weekly_reports`) that summarizes the past 7 days of sampling and emails Supervisor-level staff an HTML digest report.

---

## 3. UI/UX & Design Guidelines
- **Responsive Web Design (RWD)**: Built using Bootstrap 5.3+ to ensure smooth scaling from small iPhones to wide 4K office monitors.
- **Full Scope Dark Mode**: A unified CSS toggle using native custom CSS variables (`--bg`, `--surface`, `--text`) overriding standard browser inputs, tables, select boxes, and charts for seamless night-shift operation.
- **Information Density**: Extensive use of Badges, Color-coded Alerts (Acceptable/Warning/Reject bands), and "Stretched Link" stat cards to maximize visual parsing speed.
- **Feedback & Interactions**: Keyframes for subtle animations, instantly self-dismissing flash messages (4-second auto-collapse), and fixed-bottom "Sticky Submit" toolbars.

---

## 4. Technical Stack
- **Backend Environment**: Python 3.10+, Django 5.x Framework
- **Frontend Assets**: HTML5 Templates, Vanilla JavaScript, Bootstrap 5.3, Chart.js
- **Database Architecture**: Relational SQL (SQLite default configurable to PostgreSQL)
- **Integrations**: `django-environ` for security/SMTP mapping, `openpyxl`/`reportlab` for exports, PIL for image transposition.
