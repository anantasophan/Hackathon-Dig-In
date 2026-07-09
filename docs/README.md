# Dokumentasi Campaign Insight Generator

Folder ini berisi dokumentasi lengkap untuk setiap komponen yang dibangun dalam project Campaign Insight Generator. Setiap file mencakup penjelasan dari dua sudut pandang: **awam** (untuk stakeholder bisnis) dan **teknis** (untuk developer).

---

## Cara Membaca Dokumentasi Ini

Setiap file dokumentasi mengikuti format standar:
- **Ringkasan Singkat** — gambaran cepat tentang komponen
- **Penjelasan Awam** — cocok untuk Campaign Owner, stakeholder non-teknis
- **Penjelasan Teknis** — untuk developer yang akan mengubah atau mengintegrasikan komponen
- **Simulasi / Skenario** — contoh nyata bagaimana komponen bekerja
- **Keterkaitan** — hubungan antar komponen

---

## Index Dokumentasi

| File | Task | Komponen | Layer | Status |
|------|------|----------|-------|--------|
| [database-design.md](./database-design.md) | — | Desain Database & Data Flow | Arsitektur | ✅ |
| [task-8.3-cdk-data-stack-glue.md](./task-8.3-cdk-data-stack-glue.md) | 8.3 | DataStack — Athena Workgroup, Glue Jobs & Schedules | CDK Infrastructure | ✅ |
| [task-1.2-models.md](./task-1.2-models.md) | 1.2 | Shared Data Models (LeadRecord, dataclasses, konstanta) | Backend Shared | ✅ |
| [task-1.3-calculations.md](./task-1.3-calculations.md) | 1.3 | Shared Calculations Module | Backend Shared | ✅ |
| [task-1.4-filters.md](./task-1.4-filters.md) | 1.4 | Shared Filter Module (AND logic) | Backend Shared | ✅ |
| [task-1.5-pii-filter.md](./task-1.5-pii-filter.md) | 1.5 | PII Filter Module | Backend Shared | ✅ |
| [task-1.6-athena-client.md](./task-1.6-athena-client.md) | 1.6 | Athena Query Helper (AthenaClient, SQL builders) | Backend Shared | ✅ |
| [task-2.1-sorting.md](./task-2.1-sorting.md) | 2.1 | Sorting Utility Module | Backend Shared | ✅ |
| [task-4.1-campaign-overview-lambda.md](./task-4.1-campaign-overview-lambda.md) | 4.1 | Campaign Overview Lambda — `GET /api/campaigns/overview` | Lambda Handler | ✅ |
| [task-4.2-campaign-comparison-lambda.md](./task-4.2-campaign-comparison-lambda.md) | 4.2 | Campaign Comparison Lambda — `POST /api/campaigns/comparison` | Lambda Handler | ✅ |
| [task-4.3-time-analysis-lambda.md](./task-4.3-time-analysis-lambda.md) | 4.3 | Time Analysis Lambda — `GET /api/campaigns/time-analysis/{id}` | Lambda Handler | ✅ |
| [task-4.4-regional-performance-lambda.md](./task-4.4-regional-performance-lambda.md) | 4.4 | Regional Performance Lambda — `GET /api/campaigns/regional/{id}` | Lambda Handler | ✅ |
| [task-4.5-customer-criteria-lambda.md](./task-4.5-customer-criteria-lambda.md) | 4.5 | Customer Criteria Lambda — `GET /api/campaigns/customer-criteria/{id}` | Lambda Handler | ✅ |
| [task-4.6-similar-campaign-lambda.md](./task-4.6-similar-campaign-lambda.md) | 4.6 | Similar Campaign Lambda — `POST /api/campaigns/similar` | Lambda Handler | ✅ |
| [task-4.7-export-service-lambda.md](./task-4.7-export-service-lambda.md) | 4.7 | Export Service Lambda — `POST /api/export` (PDF/Excel/CSV) | Lambda Handler | ✅ |
| [task-4.8-auth-middleware.md](./task-4.8-auth-middleware.md) | 4.8 | Auth Middleware (JWT validation, 8-hour session) | Backend Shared | ✅ |
| [task-4.9-audit-logging.md](./task-4.9-audit-logging.md) | 4.9 | Audit Logging (DynamoDB TTL, decorator pattern) | Backend Shared | ✅ |
| [task-8.2-cdk-api-stack.md](./task-8.2-cdk-api-stack.md) | 8.2 | ApiStack — API Gateway, Lambda routing, IAM, CORS, throttling | CDK Infrastructure | ✅ |
| [task-1.3-calculations.md](./task-1.3-calculations.md) | 1.3 | Shared Calculations Module | Backend – Shared | ✅ |
| [task-1.4-filters.md](./task-1.4-filters.md) | 1.4 | Shared Filter Module | Backend – Shared | ✅ |
| [task-1.5-pii-filter.md](./task-1.5-pii-filter.md) | 1.5 | PII Filter Module | Backend – Shared | ✅ |
| [task-2.1-sorting.md](./task-2.1-sorting.md) | 2.1 | Sorting Utility Module | Backend – Shared | ✅ |
| [task-4.1-campaign-overview-lambda.md](./task-4.1-campaign-overview-lambda.md) | 4.1 | Campaign Overview Lambda — `GET /api/campaigns/overview` | Lambda Handler | ✅ |
| [task-4.2-campaign-comparison-lambda.md](./task-4.2-campaign-comparison-lambda.md) | 4.2 | Campaign Comparison Lambda — `POST /api/campaigns/comparison` | Lambda Handler | ✅ |
| [task-4.3-time-analysis-lambda.md](./task-4.3-time-analysis-lambda.md) | 4.3 | Time Analysis Lambda — `GET /api/campaigns/time-analysis/{id}` | Lambda Handler | ✅ |
| [task-4.7-export-service-lambda.md](./task-4.7-export-service-lambda.md) | 4.7 | Export Service Lambda (PDF/Excel/CSV) | Lambda | ✅ |
| [task-4.8-auth-middleware.md](./task-4.8-auth-middleware.md) | 4.8 | Auth Middleware (JWT & Session) | Shared Module | ✅ |
| [task-4.9-audit-logging.md](./task-4.9-audit-logging.md) | 4.9 | Audit Logging (DynamoDB TTL) | Shared Module | ✅ |
| [task-4.4-regional-performance-lambda.md](./task-4.4-regional-performance-lambda.md) | 4.4 | Regional Performance Lambda | Backend Lambda | ✅ |
| [task-4.5-customer-criteria-lambda.md](./task-4.5-customer-criteria-lambda.md) | 4.5 | Customer Criteria Lambda | Backend Lambda | ✅ |
| [task-4.6-similar-campaign-lambda.md](./task-4.6-similar-campaign-lambda.md) | 4.6 | Similar Campaign Lambda | Backend Lambda | ✅ |
| [task-1.2-models.md](./task-1.2-models.md) | 1.2 | Shared Data Models (LeadRecord, Request/Response dataclasses, konstanta validasi) | Backend Shared | ✅ |
| [task-1.6-athena-client.md](./task-1.6-athena-client.md) | 1.6 | Athena Query Helper (AthenaClient, polling, query builders, SQL injection prevention) | Backend Shared | ✅ |
| [task-11.5-customer-criteria-page.md](./task-11.5-customer-criteria-page.md) | 11.5 | CustomerCriteriaPage — grafik distribusi demografis & finansial nasabah | Frontend Page | ✅ |
| [task-11.6-similar-campaign-page.md](./task-11.6-similar-campaign-page.md) | 11.6 | SimilarCampaignPage — pencarian campaign serupa, kartu hasil, side-by-side detail | Frontend Page | ✅ |
| [task-11.7-export-service.md](./task-11.7-export-service.md) | 11.7 | ExportService — tombol ekspor, format selector, toast notification, auto-download | Frontend Component | ✅ |
| [task-13.2-error-handling-retry.md](./task-13.2-error-handling-retry.md) | 13.2 | Error Handling & Retry — exponential backoff, circuit breaker, ApiServiceUnavailableError, rate_limiter | Frontend + Backend | ✅ |
| [task-13.1-api-wiring.md](./task-13.1-api-wiring.md) | 13.1 | API Wiring — penyambungan frontend ke backend, audit CORS, JWT token flow | Integration | ✅ |

---

## Struktur Dokumentasi (Direncanakan)

### 🏗️ Backend — Shared Modules

| File | Task | Deskripsi |
|------|------|-----------|
| `task-1.2-models.md` | 1.2 | Data models & validasi (LeadRecord, dll) |
| `task-1.3-calculations.md` | 1.3 | Kalkulasi take_up_rate, statistik, granularitas |
| `task-1.4-filters.md` | 1.4 | Filter logic — AND intersection |
| `task-1.5-pii-filter.md` | 1.5 | PII stripping — keamanan data nasabah |
| `task-1.6-athena-client.md` | 1.6 | Athena query helper & SQL builder |
| `task-2.1-sorting.md` | 2.1 | Sorting utility — regional & similar campaigns |

### ⚡ Backend — Lambda Handlers

| File | Task | Endpoint | Deskripsi |
|------|------|----------|-----------|
| `task-4.1-campaign-overview-lambda.md` | 4.1 | GET /api/campaigns/overview | Ringkasan performa campaign |
| `task-4.2-campaign-comparison-lambda.md` | 4.2 | POST /api/campaigns/comparison | Perbandingan antar campaign |
| `task-4.3-time-analysis-lambda.md` | 4.3 | GET /api/campaigns/time-analysis/{id} | Analisis waktu take up |
| [task-4.4-regional-performance-lambda.md](./task-4.4-regional-performance-lambda.md) | 4.4 | GET /api/campaigns/regional/{id} | Performa per wilayah |
| [task-4.5-customer-criteria-lambda.md](./task-4.5-customer-criteria-lambda.md) | 4.5 | GET /api/campaigns/customer-criteria/{id} | Kriteria nasabah |
| [task-4.6-similar-campaign-lambda.md](./task-4.6-similar-campaign-lambda.md) | 4.6 | POST /api/campaigns/similar | Campaign serupa |
| `task-4.7-export-service-lambda.md` | 4.7 | POST /api/export | Ekspor data (PDF/Excel/CSV) |
| `task-4.8-auth-middleware.md` | 4.8 | Middleware | JWT auth & session management |
| `task-4.9-audit-logging.md` | 4.9 | Middleware | Audit log access |

### 🔄 Backend — Glue ETL Jobs

| File | Task | Job | Jadwal |
|------|------|-----|--------|
| `task-7.1-raw-to-clean-etl.md` | 7.1 | raw_to_clean | Daily 02:00 |
| `task-7.2-aggregate-metrics-etl.md` | 7.2 | aggregate_metrics | Daily 03:00 |
| `task-7.3-similarity-index-etl.md` | 7.3 | similarity_index | Weekly Sun 04:00 |
| `task-7.4-regional-rollup-etl.md` | 7.4 | regional_rollup | Daily 03:30 |

### ☁️ Backend — CDK Infrastructure

| File | Task | Stack | Deskripsi |
|------|------|-------|-----------|
| `task-8.1-cdk-data-stack.md` | 8.1 | DataStack | S3 buckets & DynamoDB tables |
| [task-8.2-cdk-api-stack.md](./task-8.2-cdk-api-stack.md) | 8.2 | ApiStack | API Gateway & Lambda routing | ✅ |
| `task-8.3-cdk-data-stack-glue.md` | 8.3 | DataStack (Glue) | Glue jobs & schedules |
| [task-8.4-auth-stack.md](./task-8.4-auth-stack.md) | 8.4 | AuthStack | Cognito User Pool & JWT (8h session) | ✅ |
| [task-11.2-comparison-page.md](./task-11.2-comparison-page.md) | 11.2 | CampaignComparisonPage — multi-select, tabel 5 metrik, bar chart | Frontend Page | ✅ |

### 🖥️ Frontend — Core Components

| File | Task | Komponen | Deskripsi |
|------|------|----------|-----------|
| `task-10.1-frontend-init.md` | 10.1 | React App | Setup project & routing |
| `task-10.2-auth-guard.md` | 10.2 | AuthGuard | Proteksi route & login |
| `task-10.3-dashboard-layout.md` | 10.3 | DashboardLayout | Layout & navigasi sidebar |
| `task-10.4-filter-panel.md` | 10.4 | FilterPanel | Panel filter kampanye |
| `task-10.5-api-service.md` | 10.5 | api.ts | Service layer Axios |

### 🖥️ Frontend — Pages

| File | Task | Halaman | Deskripsi |
|------|------|---------|-----------|
| [task-11.1-overview-page.md](./task-11.1-overview-page.md) | 11.1 | Campaign Overview | Halaman ringkasan kampanye | ✅ |
| `task-11.2-comparison-page.md` | 11.2 | Campaign Comparison | Halaman perbandingan |
| [task-11.3-time-analysis-page.md](./task-11.3-time-analysis-page.md) | 11.3 | Time to Take Up | Halaman analisis waktu ✅ |
| `task-11.4-regional-page.md` | 11.4 | Regional Performance | Halaman performa wilayah |
| `task-11.5-customer-criteria-page.md` | 11.5 | Customer Criteria | Halaman kriteria nasabah |
| `task-11.6-similar-campaign-page.md` | 11.6 | Similar Campaign | Halaman campaign serupa ✅ |
| `task-11.7-export-service.md` | 11.7 | Export | Komponen ekspor data |

---

## Dokumen Arsitektur

| File | Deskripsi |
|------|-----------|
| [database-design.md](./database-design.md) | Desain database, data model, simulasi alur data |

---

*Dokumentasi ini dibuat otomatis setiap kali sebuah task selesai dikerjakan.*  
*Terakhir diperbarui: Juli 2025 — ditambahkan task 13.1 (API Wiring: audit CORS, JWT token flow, pemetaan 8 endpoint frontend → Lambda)*
