//
//  DangerLevelOptionCard.swift
//  SafeVision
//
//  Created by Nike on 8/23/25.
//

import SwiftUI

struct DangerLevelOptionCard: View {
    let level: DangerLevel
    let isSelected: Bool
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 11) {
                // 막대들 (기존 dangerLevelBar 활용)
                dangerLevelBar(danger: level.keyForBar)
                // 타이틀
//                Text(level.title)
//                    .font(.title3)      // 필요시 .headline 으로 조정
//                    .foregroundStyle(.primary)
            }
            .frame(width: 70, height: 73) // 이미지처럼 큼직하게
            .padding(4)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .stroke(isSelected ? .black : Color.gray.opacity(0.3), lineWidth: 1)
                    .background(
                        RoundedRectangle(cornerRadius: 6).fill(.white)
                    )
            )
        }
        .buttonStyle(.plain) // iPad 대시보드 톤에 맞게
    }
}

enum DangerLevel: Int, CaseIterable, Identifiable {
    case low = 1, medium = 2, high = 3, critical = 4
    var id: Int { rawValue }

    var title: String {
        switch self {
        case .low: "Low"; case .medium: "Medium"; case .high: "High"; case .critical: "Critical"
        }
    }
    /// `dangerLevelBar(danger:)`가 요구하는 소문자 키
    var keyForBar: String {
        switch self {
        case .low: "low"; case .medium: "medium"; case .high: "high"; case .critical: "critical"
        }
    }
}
