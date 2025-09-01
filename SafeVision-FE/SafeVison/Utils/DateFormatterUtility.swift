//
//  DateFormatterUtility.swift
//  SafeVision
//
//  Created by KimDogyung on 8/24/25.
//
import Foundation

struct DateFormatterUtility {
    
    // MARK: - Static DateFormatter 인스턴스들 (성능 최적화)
    
    /// 서버에서 오는 ISO 8601 형식 파싱용 ("2025-08-23T20:03:36.894000")
    private static let isoFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        formatter.timeZone = TimeZone.current // 또는 TimeZone(abbreviation: "UTC")
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter
    }()
    
    /// 짧은 날짜 형식 출력용 ("2025-08-23 14:32")
    private static let displayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        formatter.timeZone = TimeZone.current
        formatter.locale = Locale.current
        return formatter
    }()
    
    /// 긴 날짜 형식 출력용 ("August 23, 2025 at 2:32 PM")
    private static let longDisplayFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateStyle = .long
        formatter.timeStyle = .short
        formatter.timeZone = TimeZone.current
        formatter.locale = Locale.current
        return formatter
    }()
    
    /// 시간만 출력용 ("14:32")
    private static let timeOnlyFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        formatter.timeZone = TimeZone.current
        formatter.locale = Locale.current
        return formatter
    }()
    
    /// 날짜만 출력용 ("2025-08-23")
    private static let dateOnlyFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = TimeZone.current
        formatter.locale = Locale.current
        return formatter
    }()
    
    // MARK: - 메인 변환 메서드들
    
    /// 서버 timestamp를 "2025-08-23 14:32" 형식으로 변환
    /// - Parameter timestamp: 서버에서 오는 ISO 8601 형식 문자열
    /// - Returns: "yyyy-MM-dd HH:mm" 형식의 문자열, 파싱 실패시 원본 반환
    static func formatToDisplayTime(from timestamp: String) -> String {
        guard let date = parseISOTimestamp(timestamp) else {
            print("⚠️ 날짜 파싱 실패: \(timestamp)")
            return timestamp // 파싱 실패시 원본 반환
        }
        return displayFormatter.string(from: date)
    }
    
    /// 서버 timestamp를 긴 형식으로 변환 ("August 23, 2025 at 2:32 PM")
    /// - Parameter timestamp: 서버에서 오는 ISO 8601 형식 문자열
    /// - Returns: 긴 형식의 날짜 문자열
    static func formatToLongDisplay(from timestamp: String) -> String {
        guard let date = parseISOTimestamp(timestamp) else {
            print("⚠️ 날짜 파싱 실패: \(timestamp)")
            return timestamp
        }
        return longDisplayFormatter.string(from: date)
    }
    
    /// 서버 timestamp에서 시간만 추출 ("14:32")
    /// - Parameter timestamp: 서버에서 오는 ISO 8601 형식 문자열
    /// - Returns: "HH:mm" 형식의 시간 문자열
    static func formatToTimeOnly(from timestamp: String) -> String {
        guard let date = parseISOTimestamp(timestamp) else {
            print("⚠️ 날짜 파싱 실패: \(timestamp)")
            return timestamp
        }
        return timeOnlyFormatter.string(from: date)
    }
    
    /// 서버 timestamp에서 날짜만 추출 ("2025-08-23")
    /// - Parameter timestamp: 서버에서 오는 ISO 8601 형식 문자열
    /// - Returns: "yyyy-MM-dd" 형식의 날짜 문자열
    static func formatToDateOnly(from timestamp: String) -> String {
        guard let date = parseISOTimestamp(timestamp) else {
            print("⚠️ 날짜 파싱 실패: \(timestamp)")
            return timestamp
        }
        return dateOnlyFormatter.string(from: date)
    }
    
    /// 현재 시간과의 차이를 상대적으로 표현 ("2 hours ago", "Just now")
    /// - Parameter timestamp: 서버에서 오는 ISO 8601 형식 문자열
    /// - Returns: 상대적 시간 표현 문자열
    static func formatToRelativeTime(from timestamp: String) -> String {
        guard let date = parseISOTimestamp(timestamp) else {
            print("⚠️ 날짜 파싱 실패: \(timestamp)")
            return timestamp
        }
        
        let now = Date()
        let timeInterval = now.timeIntervalSince(date)
        
        let minutes = Int(timeInterval / 60)
        let hours = Int(timeInterval / 3600)
        let days = Int(timeInterval / 86400)
        
        if timeInterval < 60 {
            return "Just now"
        } else if minutes < 60 {
            return "\(minutes) minute\(minutes == 1 ? "" : "s") ago"
        } else if hours < 24 {
            return "\(hours) hour\(hours == 1 ? "" : "s") ago"
        } else if days < 7 {
            return "\(days) day\(days == 1 ? "" : "s") ago"
        } else {
            // 7일 이상이면 정확한 날짜 표시
            return formatToDisplayTime(from: timestamp)
        }
    }
    
    // MARK: - Private Helper Methods
    
    /// ISO 8601 형식의 timestamp를 Date 객체로 파싱
    /// - Parameter timestamp: 서버에서 오는 ISO 8601 형식 문자열
    /// - Returns: Date 객체, 파싱 실패시 nil
    private static func parseISOTimestamp(_ timestamp: String) -> Date? {
        // 다양한 형식의 ISO 8601을 처리하기 위한 시도
        let formatters = [
            isoFormatter, // "2025-08-23T20:03:36.894000"
            createFormatter("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"), // "2025-08-23T20:03:36.894Z"
            createFormatter("yyyy-MM-dd'T'HH:mm:ss'Z'"), // "2025-08-23T20:03:36Z"
            createFormatter("yyyy-MM-dd'T'HH:mm:ss"), // "2025-08-23T20:03:36"
        ]
        
        for formatter in formatters {
            if let date = formatter.date(from: timestamp) {
                return date
            }
        }
        
        // iOS 10+ 에서 사용 가능한 ISO8601DateFormatter도 시도
        if #available(iOS 10.0, *) {
            let isoFormatter = ISO8601DateFormatter()
            isoFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = isoFormatter.date(from: timestamp) {
                return date
            }
        }
        
        return nil
    }
    
    /// DateFormatter 생성 헬퍼 메서드
    /// - Parameter format: 날짜 형식 문자열
    /// - Returns: 설정된 DateFormatter
    private static func createFormatter(_ format: String) -> DateFormatter {
        let formatter = DateFormatter()
        formatter.dateFormat = format
        formatter.timeZone = TimeZone.current
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter
    }
}
