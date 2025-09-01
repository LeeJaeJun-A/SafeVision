//
//  DropdownOverlayViewModel.swift
//  SafeVision
//
//  Created by Nike on 8/23/25.
//

import SwiftUI

final class DropdownOverlayViewModel: ObservableObject {
    @Published var isOpen: Bool = false
    @Published var anchor: CGRect = .zero
    @Published var options: [DetectConditionType] = []

    func open(anchor: CGRect, options: [DetectConditionType]) {
        self.anchor = anchor
        self.options = options
        withAnimation(.easeOut(duration: 0.38)) { self.isOpen = true }
    }

    func close() {
        withAnimation(.easeInOut(duration: 0.45)) { self.isOpen = false }
    }
}
