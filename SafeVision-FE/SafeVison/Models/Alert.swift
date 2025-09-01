//
//  Alert.swift
//  SafeVision
//
//  Created by KimDogyung on 8/24/25.
//


import Foundation

struct Violation: Codable, Hashable {
    let position: [Double]?
    let entityId: String?
    let timestamp: String?
    let videoId: String?
    let objects: [String]?
    
    // collision_risk 전용
    let distance: Double?
    let minDistance: Int?
    let collisionRisk: Bool?
    
    // fall_detection 전용
    let preDuration: Double?
    let postDuration: Double?
    let yChange: Double?
    let timeDuration: Int?
    let frameGap: Int?
    let fallDetected: Bool?
    let recordVideo: Bool?
    
    enum CodingKeys: String, CodingKey {
        case position
        case entityId = "entity_id"
        case timestamp
        case videoId = "video_id"
        case objects
        case distance
        case minDistance = "min_distance"
        case collisionRisk = "collision_risk"
        case preDuration = "pre_duration"
        case postDuration = "post_duration"
        case yChange = "y_change"
        case timeDuration = "time_duration"
        case frameGap = "frame_gap"
        case fallDetected = "fall_detected"
        case recordVideo = "record_video"
    }
}

// ✅ 서버 응답 'detail' 속성의 실제 구조에 맞게 수정
struct AlertDetail: Codable, Hashable {
    let ruleId: String
    let ruleType: String
    let violations: [Violation]
    let summary: String
    
    enum CodingKeys: String, CodingKey {
        case ruleId = "rule_id"
        case ruleType = "rule_type"
        case violations
        case summary
    }
}

// Alert 모델 (200 응답용)
struct Alert: Codable, Identifiable, Hashable {
    let id: String
    let ruleId: String
    let ruleType: String
    let tsMs: Int
    let summary: String
    // ✅ detail 속성 타입을 새로운 AlertDetail 모델로 변경
    let detail: AlertDetail
    let createdAt: String
    let videoId: String
    let frameNumber: Int
    let severity: String
    let status: String
    // ✅ processedAt 속성을 옵셔널(Optional) String으로 변경 (null 값 처리)
    let processedAt: String?
    let videoClipPath: String
    
    enum CodingKeys: String, CodingKey {
        case id = "alertId"
        case ruleId = "rule_id"
        case ruleType = "rule_type"
        case tsMs = "ts_ms"
        case summary
        case detail
        case createdAt = "created_at"
        case videoId = "video_id"
        case frameNumber = "frame_number"
        case severity
        case status
        case processedAt = "processed_at"
        case videoClipPath = "video_clip_path"
    }
}



extension Alert {
    
    var formattedCreatedAt: String {
        return DateFormatterUtility.formatToDisplayTime(from: createdAt)
    }
    
    
    var capitalizedSeverity: String {
        return severity.capitalized
    }
    
    /// status의 첫 글자를 대문자로 변환하고 언더스코어를 공백으로 변환
    /// ("in_progress" → "In Progress", "unprocessed" → "Unprocessed")
    var formattedStatus: String {
        return status.replacingOccurrences(of: "_", with: " ").capitalized
    }
    
    var makeStringStatus: String {
        switch status {
        case "resolved":
            return "Resolved"
        case "unprocessed":
            return "Unconfirmed"
        case "in_progress":
            return "In Progress"
        case "completed":
            return "Resolved"
        case "processing":
            return "In Progress"
        default:
            return "Unknown"
        }
    }
    
    static var mocks: [Alert] {
        [
            // 1. collision_risk
            Alert(
                id: UUID().uuidString,
                ruleId: "RULE-001",
                ruleType: "collision_risk",
                tsMs: 1724479920000,
                summary: "Collision Risk: 1 incident detected",
                detail: AlertDetail(
                    ruleId: "RULE-001",
                    ruleType: "collision_risk",
                    violations: [
                        Violation(
                            position: [356.3, 218.5],
                            entityId: "person_0_machine_1",
                            timestamp: "2025-08-23T14:32:00Z",
                            videoId: "cctv1-id",
                            objects: ["person_0", "machine_1"],
                            distance: 35.2,
                            minDistance: 50,
                            collisionRisk: true,
                            preDuration: nil,
                            postDuration: nil,
                            yChange: nil,
                            timeDuration: nil,
                            frameGap: nil,
                            fallDetected: nil,
                            recordVideo: nil
                        )
                    ],
                    summary: "Collision Risk: 1 incident detected"
                ),
                createdAt: "2025-08-23T14:32:00Z",
                videoId: "cctv1-id",
                frameNumber: 40,
                severity: "low",
                status: "unprocessed",
                processedAt: nil,
                videoClipPath: "cctv1.mp4"
            ),
            
            // 2. fall_detection
            Alert(
                id: UUID().uuidString,
                ruleId: "RULE-002",
                ruleType: "fall_detection",
                tsMs: 1724477820000,
                summary: "Fall Detected: 1 incident",
                detail: AlertDetail(
                    ruleId: "RULE-002",
                    ruleType: "fall_detection",
                    violations: [
                        Violation(
                            position: [261.0, 143.8],
                            entityId: "worker_1",
                            timestamp: "2025-08-23T13:57:00Z",
                            videoId: "cctv2-id",
                            objects: ["worker_1"],
                            distance: nil,
                            minDistance: nil,
                            collisionRisk: nil,
                            preDuration: 1.5,
                            postDuration: 3.5,
                            yChange: 74.8,
                            timeDuration: 0,
                            frameGap: 24,
                            fallDetected: true,
                            recordVideo: true
                        )
                    ],
                    summary: "Fall Detected: 1 incident"
                ),
                createdAt: "2025-08-23T13:57:00Z",
                videoId: "cctv2-id",
                frameNumber: 906,
                severity: "medium",
                status: "processing",
                processedAt: nil,
                videoClipPath: "cctv2.mp4"
            ),
            
            // 3. zone_breach (similar structure to collision_risk)
            Alert(
                id: UUID().uuidString,
                ruleId: "RULE-003",
                ruleType: "zone_breach",
                tsMs: 1724473500000,
                summary: "Unauthorized Zone Entry Detected",
                detail: AlertDetail(
                    ruleId: "RULE-003",
                    ruleType: "zone_breach",
                    violations: [
                        Violation(
                            position: [345.1, 789.2],
                            entityId: "intruder_1",
                            timestamp: "2025-08-23T12:45:00Z",
                            videoId: "cctv3-id",
                            objects: ["intruder_1", "restricted_zone"],
                            distance: 0.0,
                            minDistance: 0,
                            collisionRisk: true,
                            preDuration: nil,
                            postDuration: nil,
                            yChange: nil,
                            timeDuration: nil,
                            frameGap: nil,
                            fallDetected: nil,
                            recordVideo: nil
                        )
                    ],
                    summary: "Unauthorized Zone Entry Detected"
                ),
                createdAt: "2025-08-23T12:45:00Z",
                videoId: "cctv3-id",
                frameNumber: 240,
                severity: "high",
                status: "completed",
                processedAt: "2025-08-23T12:48:00Z",
                videoClipPath: "cctv3.mp4"
            ),
            
            Alert(
                id: UUID().uuidString,
                ruleId: "RULE-002",
                ruleType: "fall_detection",
                tsMs: 1724477820000,
                summary: "Close to Moving Vehicle",
                detail: AlertDetail(
                    ruleId: "RULE-002",
                    ruleType: "fall_detection",
                    violations: [
                        Violation(
                            position: [261.0, 143.8],
                            entityId: "worker_1",
                            timestamp: "2025-08-23T13:57:00Z",
                            videoId: "cctv2-id",
                            objects: ["worker_1"],
                            distance: nil,
                            minDistance: nil,
                            collisionRisk: nil,
                            preDuration: 1.5,
                            postDuration: 3.5,
                            yChange: 74.8,
                            timeDuration: 0,
                            frameGap: 24,
                            fallDetected: true,
                            recordVideo: true
                        )
                    ],
                    summary: "Fall Detected: 1 incident"
                ),
                createdAt: "2025-08-23T13:57:00Z",
                videoId: "cctv2-id",
                frameNumber: 906,
                severity: "medium",
                status: "processing",
                processedAt: nil,
                videoClipPath: "cctv2.mp4"
            ),
        ]
    }
}
