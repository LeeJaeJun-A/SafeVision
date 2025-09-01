# Safe Vision – Smart Safety Monitoring System

## Overview

Safe Vision is an **iPad (iOS) app** developed by **Team WaveMakers** during **Junction Asia 2025 Hackathon**.
It is a **smart safety monitoring system** that leverages **AI-powered CCTV video analysis** and **real-time alerts** to reduce industrial accidents caused by a lack of systematic safety management.

## Problem Statement

Current CCTV monitoring systems suffer from:

* Low focus across multiple camera feeds
* Operator fatigue due to shift work
* Inconsistent or subjective judgment
* Only post-incident evidence, limited real-time response

## Core Idea

* **AI real-time analysis**: YOLO-based object detection + rule engine
* **Instant alerts**: Delivered directly to managers’ iPads via SSE
* **Rule-based detection**: Distance violations, zone entries, overspeeding, collision risks, fall detection, and more
* **Cloud-native architecture**: Serverless processing with AWS Rekognition, Kinesis, Flink, and DynamoDB

## Key Features

### iOS App (Swift, iPadOS)

* Receive **real-time alerts** via SSE
* View **detailed incident clips** before and after detection
* Manage and apply **custom detection rules** directly from the app
* Optimized for **on-site safety managers**

### Backend (FastAPI)

* Video upload & analysis APIs
* YOLO object detection and event generation
* JSON-based dynamic rule system
* MongoDB alert history storage
* Real-time alerts via SSE

### Example Detection Rules

* `distance_below`: Unsafe proximity violation
* `zone_entry`: Restricted zone entry
* `speed_over`: Overspeed detection
* `collision_risk`: Collision risk (distance + velocity + direction)
* `fall_detection`: Fall detection based on sudden Y-axis drop

## System Architecture

1. CCTV or drone video input
2. YOLO object detection
3. Event transformation & rule matching
4. Real-time processing with Apache Flink (exactly-once guarantees)
5. Rules stored in DynamoDB/S3 with hot-swap support
6. Alerts pushed to iPad via SSE
7. Optional integration with smartwatches and emergency services

## Expected Impact

* **24/7 unmanned monitoring** → Reduced labor cost & fatigue
* **Real-time response** → Faster decisions and quicker actions
* **Consistent rule enforcement** → No subjective differences between operators
* **Scalability** → Applicable not only to CCTV but also to drones and next-gen video technologies

## Installation & Usage

### Backend

```bash
# 1. Run MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:latest

# 2. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### iOS App

* Built with Swift for iPadOS
* Allow HTTP/SSE connections in **Info.plist**:

```swift
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

* SSE alert stream endpoint:

```
http://[SERVER_IP]/api/v1/alerts/sse/alerts
```

## Team

**Team WaveMakers**
Developed at **Junction Asia 2025 Hackathon**