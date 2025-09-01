//
//  DropdownField.swift
//  SafeVision
//
//  Created by Nike on 8/23/25.
//

import SwiftUI

struct DropdownField: View {
    let title: String
    let displayText: String
    let onTap: (CGRect) -> Void

    @State private var fieldRect: CGRect = .zero

    var body: some View {
        Button {
            onTap(fieldRect)
        } label: {
            HStack {
                Text(displayText).foregroundColor(.primary).lineLimit(1)
                Spacer()
                Image(systemName: "chevron.down")
                    .foregroundColor(.black)
                    .font(.system(size: 18, weight: .regular))
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 18)
            .frame(height: 56)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                    .background(
                        RoundedRectangle(cornerRadius: 8).fill(Color.white)
                    )
            )
        }
        .buttonStyle(.plain)
        .background(
            GeometryReader { geo in
                Color.clear
                    .onAppear { fieldRect = geo.frame(in: .named("container")) }
                    .onChange(of: geo.frame(in: .named("container")).origin) { _ in
                        fieldRect = geo.frame(in: .named("container"))
                    }
            }
        )
        .accessibilityLabel(Text(title))
    }
}
