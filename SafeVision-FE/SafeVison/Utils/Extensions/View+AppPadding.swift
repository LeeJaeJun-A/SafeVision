//
//  SSEService.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import SwiftUI

struct AppPadding: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(.horizontal, 48)
    }
}

extension View {
    func appPadding() -> some View {
        self.modifier(AppPadding())
    }
}
