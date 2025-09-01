//
//  RulesResonse.swift
//  SafeVision
//
//  Created by KimDogyung on 8/24/25.
//
import Foundation

struct RulesResponse: Codable {
    let success: Bool
    let data: [Rule]
    let totalCount: Int
    
    enum CodingKeys: String, CodingKey {
        case success, data
        case totalCount = "total_count"
    }
}


struct Rule: Codable {
    let id: String
    let name: String
    let type: String
    let enabled: Bool
    let severity: String
    let description: String
    let params: RuleParams
}

struct RuleParams: Codable {
    let zone: Zone?
    let duration: Int?
    let labels: [String]?
    let maxSpeed: Int?
    let maxCount: Int?
    let minFallPixels: Int?
    let maxFrameGap: Int?
    let frameRange: [Int]?
    let minDistance: Int?
    let personLabels: [String]?
    let line: Line?
    
    enum CodingKeys: String, CodingKey {
        case zone, duration, labels
        case maxSpeed = "max_speed"
        case maxCount = "max_count"
        case minFallPixels = "min_fall_pixels"
        case maxFrameGap = "max_frame_gap"
        case frameRange = "frame_range"
        case minDistance = "min_distance"
        case personLabels = "person_labels"
        case line
    }
}


struct Zone: Codable {
    let id: String
    let name: String
    let polygon: [[Int]]
    let dangerLevel: String?
    
    enum CodingKeys: String, CodingKey {
        case id, name, polygon
        case dangerLevel = "danger_level"
    }
}

// ✅ Line 모델 정의
struct Line: Codable {
    let id: String
    let name: String
    let points: [[Int]]
    let direction: String
}
