
# # MediResilience AI
# An AI-Driven, Offline-First Medicine Stockout Prediction, Redistribution and Supply Chain Resilience Platform
MediResilience AI

AI-Powered Essential Medicine Stockout Prediction,
Redistribution and Supply Chain Resilience Platform.

## Project Overview

MediResilience AI is a multi-level healthcare supply-chain
management platform designed to improve essential medicine
availability at district and healthcare facility levels.

## Main Features

- Multi-role healthcare supply-chain management
- Medicine inventory and batch tracking
- Consumption and replenishment management
- AI-powered demand forecasting
- Stockout risk prediction
- Intelligent inter-facility redistribution
- Automated notifications
- Offline-first medicine stock reporting
- District, regional and national dashboards
- Analytics and reporting

## Technology Stack

### Backend
- Python
- Django
- Django REST Framework
- PostgreSQL

### Frontend
- Next.js
- TypeScript
- Tailwind CSS

### Artificial Intelligence
- Scikit-learn
- XGBoost
- PyTorch
- Google OR-Tools

### Infrastructure
- Docker
- Redis
- Celery
- Nginx
- GitHub Actions

## Project Structure

- backend/: Django backend
- frontend/: Next.js frontend
- ml-service/: AI and ML services
- infrastructure/: Deployment configuration
- docs/: Technical documentation
- scripts/: Automation scripts

## Development Status

Phase 1: Architecture and Requirements
Phase 2: Development Environment Setup


his is a healthcare supply-chain innovation challenge. It is asking you to design and build a digital or technology-enabled solution that prevents shortages (stockouts) of essential medicines in hospitals, health centres, and district-level health facilities.

In simple terms, the challenge is:

How can we ensure that essential medicines are always available at health facilities, even when the logistics systems and funding that previously supported medicine distribution are reduced or withdrawn?

Let's break it down.
1. Understanding the problem
The statement has three important parts.

A. Reduce stockouts of essential medicines

A stockout happens when a health facility runs out of a medicine that patients need.

Examples:
- A health centre runs out of antibiotics.
- A hospital runs out of insulin.
- A clinic has insufficient malaria medicines.
- A health facility runs out of vaccines or essential maternal-health medicines.
B. At district and facility level

The solution should work at two levels:
Level	Main responsibility
District	Monitor medicine availability across health facilities, coordinate redistribution, manage procurement and replenishment.
Health facility	Record medicine consumption, monitor stock levels, report shortages and request replenishment.

C. Countries facing drawdown of US Government-funded logistics management capacity

This is particularly important.

Some countries have relied on US Government-funded programmes, technical experts, logistics personnel, supply-chain systems, and operational support to manage medicine distribution.

A drawdown means that this external support is being reduced, transitioned, or withdrawn.

Consequently, countries need sustainable solutions that allow their own ministries of health, district health offices, and facilities to manage medicine supply chains with less external assistance.
2. What kind of solution are they expecting?
They are likely expecting a working prototype of a Digital Logistics Management Information System (eLMIS), potentially enhanced with AI and optimization.

For example, imagine a system called:
MediTrack AI
AI-powered Essential Medicine Availability and Distribution Platform

# MediResilience AI
# An AI-Driven, Offline-First Medicine Stockout Prediction, Redistribution and Supply Chain Resilience Platform


The system could have the following modules:
Module	Function
Medicine inventory	Monitor available medicines at each facility.
AI demand forecasting	Predict how much medicine each facility will need.
Stockout prediction	Identify medicines likely to run out in the next 7–30 days.
Automated alerts	Notify pharmacists and district officers about critical shortages.
Inter-facility redistribution	Identify nearby facilities with surplus stock.
Replenishment management	Generate medicine requests and track approvals.
District dashboard	Monitor medicine availability across all facilities.
Analytics	Measure stockout rates, consumption, expiry and distribution efficiency.

3. Example of how it would work
Imagine three health facilities in an Ethiopian district:
Health facility	Amoxicillin stock	Situation
Health Centre A	500 tablets	Overstock
Health Centre B	25 tablets	Critical
Health Centre C	200 tablets	Normal

Suppose Health Centre B consumes approximately 20 tablets daily.

The system calculates that it has approximately 1.25 days of stock remaining.
Critical stock alert
The system then:
1. Notifies the district pharmacist.
2. Identifies Health Centre A as a potential redistribution source.
3. Recommends transferring 150 tablets from A to B, subject to minimum stock requirements and expiry checks.
4. Generates a digital transfer request.
5. Tracks approval and delivery.
6. Updates both facilities' inventory records.
This helps prevent a stockout without waiting for a new procurement cycle.
4. Where does AI come in?
This is where you can introduce a more innovative research and engineering component.

I would consider five AI capabilities:
- Demand forecasting: LSTM, Temporal Fusion Transformer or XGBoost to predict medicine consumption.
- Stockout prediction: Random Forest, XGBoost or LightGBM to predict the probability of a medicine running out.
- Anomaly detection: Identify unusual consumption, possible reporting errors and unexpected inventory changes.
- Redistribution optimization: Optimization algorithms to determine which facilities should transfer medicines to other facilities.
- Risk prioritization: Rank facilities based on stockout risk, patient demand, medicine criticality and replenishment lead time.
An important consideration is that AI should work with incomplete and delayed data. The solution should not depend on every facility having continuous internet access or highly trained logistics personnel.
5. Why is this relevant to Ethiopia?
This challenge has a direct connection to Ethiopia's healthcare supply chain.

Ethiopia already has initiatives such as Dagu 2.1, a health commodity management information system supported through the US President's Malaria Initiative. It provides facility-level consumption information and automated alerts. A reported survey in selected Addis Ababa facilities found a 20% increase in commodity availability following deployment. 
pmi.gov


Therefore, a new solution should not simply recreate an existing inventory application. It should investigate interoperability with existing systems, strengthen district-level decision-making, and address gaps in forecasting, redistribution, offline reporting and local operational sustainability.

The broader concern is real: UNAIDS documented supply-chain management challenges affecting HIV commodity distribution in multiple countries, including Ethiopia.


# CELL 2.24
.\backend\.venv\Scripts\Activate.ps1