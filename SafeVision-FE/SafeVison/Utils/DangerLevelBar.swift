//
//  DangerLevelBar.swift
//  SafeVision
//
//  Created by Nike on 8/23/25.
//
import SwiftUI

func dangerLevelBar(danger: String) -> some View {
    var numberOfBars: Int
    var barColor: Color
    
    switch danger {
    case "critical":
        numberOfBars = 4
        barColor = Color(hex: "#F94C4C")
    case "high":
        numberOfBars = 3
        barColor = Color(hex: "#FF9945")
    case "medium":
        numberOfBars = 2
        barColor = Color(hex: "#FFD651")
    case "low":
        numberOfBars = 1
        barColor = Color(hex: "#5AEE7F")
    default:
        numberOfBars = 0
        barColor = .clear
    }
    
    return VStack(spacing: 4) {
        HStack(spacing: 4) {
            ForEach(0..<4, id: \.self) { bar in
                Rectangle()
                    .fill(bar < numberOfBars ? barColor : Color(hex: "#D9D9D9"))
                    .frame(width: 8, height: 28)
                    .cornerRadius(3)
            }
        }
        
        Text(danger)
            .font(.system(size: 14))
            .foregroundStyle(barColor)
    }
}
