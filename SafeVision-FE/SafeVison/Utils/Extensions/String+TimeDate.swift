//
//  String+TimeDate.swift
//  SafeVision
//
//  Created by KimDogyung on 8/24/25.
//

import Foundation

extension String {
    
    /// String에서 직접 날짜 변환을 수행할 수 있는 편의 메서드들
    
    /// "2025-08-23 14:32" 형식으로 변환
    var toDisplayTime: String {
        return DateFormatterUtility.formatToDisplayTime(from: self)
    }
    
    /// 긴 형식으로 변환
    var toLongDisplayTime: String {
        return DateFormatterUtility.formatToLongDisplay(from: self)
    }
    
    /// 시간만 추출
    var toTimeOnly: String {
        return DateFormatterUtility.formatToTimeOnly(from: self)
    }
    
    /// 날짜만 추출
    var toDateOnly: String {
        return DateFormatterUtility.formatToDateOnly(from: self)
    }
    
    /// 상대적 시간 표현
    var toRelativeTime: String {
        return DateFormatterUtility.formatToRelativeTime(from: self)
    }
}
