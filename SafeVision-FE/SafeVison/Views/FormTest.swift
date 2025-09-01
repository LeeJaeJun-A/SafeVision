import SwiftUI

struct FormTest: View {
    @Environment(\.dismiss) private var dismiss

    @State var draft: DetectCondition = DetectCondition(
        id: nil,
        name: "",
        type: .fall,
        description: "",
        rate: 2,
        durationSec: 0   // 기본 0초(원하는 값으로)
    )
    var onSave: (DetectCondition) -> Void = { _ in }

    @StateObject private var dropdownVM = DropdownOverlayViewModel()
    @State private var typeFieldWidth: CGFloat = 0

    var body: some View {
        ZStack(alignment: .topLeading) {
            VStack(spacing: 16) {
                // Type
                VStack {
                    HStack { Text("Type"); Spacer() }
                    DropdownField(
                        title: "Type",
                        displayText: draft.type.rawValue
                    ) { anchor in
                        typeFieldWidth = anchor.width
                        dropdownVM.open(anchor: anchor, options: DetectConditionType.allCases)
                    }
                    .frame(maxWidth: 360)
                }

                // Description
                VStack {
                    HStack { Text("Description"); Spacer() }
                    TextField("ex. 3 people in room 3", text: $draft.description, axis: .vertical)
                        .lineLimit(2...4)
                        .textFieldStyle(.roundedBorder)
                }

                VStack {
                    HStack { Text("Risk Level"); Spacer() }
                        // 가로 4개 배치 (이미지와 동일)
                        HStack(spacing: 16) {
                            ForEach(DangerLevel.allCases) { level in
                                DangerLevelOptionCard(
                                    level: level,
                                    isSelected: draft.rate == level.rawValue,
                                    onTap: { draft.rate = level.rawValue }
                                )
                            }
                        }
                    
                }

                HStack {
                    Spacer()
                    Button("Save") {
                        onSave(draft)
                        dismiss()
                    }
                    .buttonStyle(.bordered)
                    .cornerRadius(8)
                    .foregroundColor(.white)
                    .background(Color.gray)
                }
            }

            if dropdownVM.isOpen {
                // 바깥 탭 → 닫기
                Color.black.opacity(0.001)
                    .ignoresSafeArea()
                    .onTapGesture { dropdownVM.close() }
                    .zIndex(998)

                // 드롭다운 바 (다른 뷰는 그대로)
                OverlayDropBar(isOpen: dropdownVM.isOpen, maxHeight: 280) {
                    OverlayDropdownList(
                        options: dropdownVM.options,
                        onSelect: { sel in
                            draft.type = sel
                            dropdownVM.close()
                        }
                    )
                }
                .frame(width: typeFieldWidth)
                .offset(x: dropdownVM.anchor.minX, y: dropdownVM.anchor.maxY + 6)
                .zIndex(999)
            }
        }
        .coordinateSpace(name: "container")
        .navigationTitle("Detect Condition")
        
    }
}

#Preview(traits: .landscapeLeft) {
    FormTest()
}
