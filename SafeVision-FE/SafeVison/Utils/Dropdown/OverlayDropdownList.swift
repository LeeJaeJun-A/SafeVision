//
//  OverlayDropdownList.swift
//  SafeVision
//
//  Created by Nike on 8/23/25.
//

import SwiftUI

struct OverlayDropdownList: View {
    let options: [DetectConditionType]
    let onSelect: (DetectConditionType) -> Void

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 0) {
                ForEach(options, id: \.id) { option in
                    Button {
                        onSelect(option)
                    } label: {
                        HStack {
                            Text(option.rawValue)
                                .foregroundColor(.white)
                                .padding(.vertical, 20)
                                .padding(.horizontal, 20)
                                .font(.system(size: 18, weight: .regular))
                            Spacer()
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }
}
