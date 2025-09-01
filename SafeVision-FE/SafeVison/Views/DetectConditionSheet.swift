//
//  DetectConditionSheet.swift
//  SafeVision
//
//  Created by Nike on 8/23/25.
//

import SwiftUI

private struct PaddedRoundedTextFieldStyle: TextFieldStyle {
    var vPadding: CGFloat = 18
    var hPadding: CGFloat = 20
    var cornerRadius: CGFloat = 8
    var strokeColor: Color = Color.gray.opacity(0.35)
    var fillColor: Color = Color.white

    func _body(configuration: TextField<_Label>) -> some View {
        configuration
            .padding(.vertical, vPadding)
            .padding(.horizontal, hPadding)
            .background(
                RoundedRectangle(cornerRadius: cornerRadius)
                    .fill(fillColor)
            )
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(strokeColor, lineWidth: 1)
            )
    }
}


struct DetectConditionSheet: View {
    @ObservedObject var vm: DetectConditionViewModel
    var onClose: () -> Void

    @State private var mode: Mode = .list
    @State private var editingDraft: DetectCondition? = nil

    private enum Mode { case list, form }

    var body: some View {
        NavigationStack {
            headerView
            
            // Loading indicator
            if vm.isLoadingRules {
                VStack {
                    ProgressView("규칙을 불러오는 중...")
                        .padding()
                    Spacer()
                }
            } else {
                // Content container: fixed frame, no layout jump
                ZStack(alignment: .topLeading) {
                    listModeView
                    formModeView
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .transaction { $0.animation = nil } // prevent implicit layout animations
            }
            
            // Error message
//            if let errorMessage = vm.rulesErrorMessage {
//                Text("오류: \(errorMessage)")
//                    .foregroundColor(.red)
//                    .padding()
//            }
        }
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(action: { onClose() }) {
                    Label("닫기", systemImage: "xmark")
                }
            }
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 24)
        .onAppear {
            vm.loadRulesAsConditions()
        }
    }
    
    // MARK: - Header View
    private var headerView: some View {
        HStack {
            Text("Alerts Settings")
                .font(.system(size: 22, weight: .medium))
            Spacer()
            Button(action: { onClose() }) {
                Image(systemName: "xmark")
            }
            .foregroundColor(.black)
        }
    }
    
    // MARK: - List Mode View
    private var listModeView: some View {
        VStack(spacing: 0) {
            conditionsScrollView
            addSettingButton
        }
        .opacity(mode == .list ? 1 : 0)
    }
    
    private var conditionsScrollView: some View {
        ScrollView {
            LazyVStack(spacing: 8) {
                ForEach(vm.serverConditions) { cond in
                    conditionRowView(cond)
                        .padding(.vertical, 4)
                }
            }
        }
    }
    
    private func conditionRowView(_ cond: DetectCondition) -> some View {
        ZStack(alignment: .topTrailing) {
            conditionButton(cond)
            deleteButton(cond)
        }
    }
    
    private func conditionButton(_ cond: DetectCondition) -> some View {
        Button {
            editingDraft = cond
            mode = .form
        } label: {
            ConditionCardView(cond: cond)
        }
        .buttonStyle(.plain)
    }
    
    private func deleteButton(_ cond: DetectCondition) -> some View {
        VStack {
            Spacer()
            Button(action: {
                if cond.name != "Fall Detection" && cond.name != "Collision Risk" {
                    vm.deleteServerCondition(cond)
                }
            }) {
                Image(systemName: "minus.circle")
                    .foregroundColor(.gray)
                    .padding()
            }
            .buttonStyle(.plain)
            Spacer()
        }
    }
    
    private var addSettingButton: some View {
        HStack {
            Spacer()
            Button {
                editingDraft = DetectCondition(
                    id: nil,
                    name: "",
                    type: .fall,
                    description: "",
                    rate: 3,
                    durationSec: 5
                )
                mode = .form
            } label: {
                addSettingButtonLabel
            }
            .padding(.top, 8)
        }
    }
    
    private var addSettingButtonLabel: some View {
        Label("Add Setting", systemImage: "plus")
            .font(.system(size: 20, weight: .semibold))
            .foregroundColor(.white)
            .padding(.horizontal, 28.5)
            .padding(.vertical, 16)
            .background(Color(hex: "#0E0E0E"))
            .cornerRadius(8)
    }
    
    // MARK: - Form Mode View
    private var formModeView: some View {
        Group {
            if let draft = editingDraft {
                DetectConditionFormInline(
                    draft: draft,
                    onCancel: {
                        mode = .list
                        editingDraft = nil
                    },
                    onSave: { saved in
//                        vm.insert(saved)
                        vm.postCondition(saved) { result in
                            switch result {
                            case .success:
                                print("🎉 저장+전송 완료")
                            case .failure(let err):
                                print("⚠️ 전송 실패:", err.localizedDescription)
                            }
                        }
                        mode = .list
                        editingDraft = nil
                    }
                )
            }
        }
        .opacity(mode == .form ? 1 : 0)
    }
}

private struct ConditionCardView: View {
    let cond: DetectCondition

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            
            conditionHeader
            conditionDescription
        }
        .padding()
        .background(conditionBackground)
    }
    
    private var conditionHeader: some View {
        HStack(spacing: 8) {
            
            Text(cond.name)
                .foregroundColor(.black)
                .font(.system(size: 20, weight: .regular))
            
//            Text(cond.type.rawValue)
//                .foregroundColor(.black)
//                .font(.system(size: 14, weight: .regular))
            
            Text(severityText)
                .font(.system(size: 14, weight: .regular))
                .foregroundColor(severityColor)
            
            Spacer()
        }
    }
    
    private var conditionDescription: some View {
        Text(cond.description)
            .font(.system(size: 14, weight: .regular))
            .foregroundColor(.gray)
            .frame(width: 310, alignment: .leading)
    }
    
    private var conditionBackground: some View {
        RoundedRectangle(cornerRadius: 8)
            .stroke(Color(hex: "#EAECF4"))
    }
    
    private var severityText: String {
        switch cond.rate {
        case let r where r >= 4: return "Critical"
        case 3: return "High"
        case 2: return "Medium"
        default: return "Low"
        }
    }
    
    private var severityColor: Color {
        switch cond.rate {
        case let r where r >= 4: return Color(hex: "#F94C4C")
        case 3: return Color(hex: "#FF9945")
        case 2: return Color(hex: "#FFD651")
        case 1: return Color(hex: "#5AEE7F")
        default: return .gray
        }
    }
}

private struct DetectConditionFormInline: View {
    @Environment(\.dismiss) private var dismiss

    @State var draft: DetectCondition
    var onCancel: () -> Void
    var onSave: (DetectCondition) -> Void

    @StateObject private var dropdownVM = DropdownOverlayViewModel()
    @State private var typeFieldWidth: CGFloat = 0

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(alignment: .leading, spacing: 16) {
                nameField
                typeField
                descriptionField
                riskLevelField
                durationField
                
                Spacer()
                saveButton
            }
            .padding(.top, 8)
            .overlay(alignment: .topLeading) {
                dropdownOverlay
            }
            .coordinateSpace(name: "container")
        }
    }
    
    // MARK: - Form Fields
    private var nameField: some View {
        VStack {
            fieldLabel("Name")
            TextField("ex. Night shift alert", text: $draft.name)
                .textFieldStyle(PaddedRoundedTextFieldStyle())
                .font(.system(size: 18, weight: .regular))
        }
    }
    
    private var typeField: some View {
        VStack {
            fieldLabel("Type")
            DropdownField(
                title: "Type",
                displayText: draft.type.rawValue
            ) { anchor in
                typeFieldWidth = anchor.width
                dropdownVM.open(anchor: anchor, options: DetectConditionType.allCases)
            }
        }
    }
    
    private var descriptionField: some View {
        VStack {
            fieldLabel("Description")
            TextField("ex. 3 people in room 3", text: $draft.description, axis: .vertical)
                .lineLimit(2...4)
                .textFieldStyle(PaddedRoundedTextFieldStyle())
                .font(.system(size: 18, weight: .regular))
        }
    }
    
    private var riskLevelField: some View {
        VStack {
            fieldLabel("Risk Level")
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
    }
    
    private var durationField: some View {
        VStack {
            fieldLabel("Duration (seconds)")
            TextField("ex. 300", value: $draft.durationSec, format: .number)
                .keyboardType(.numberPad)
                .textFieldStyle(PaddedRoundedTextFieldStyle())
                .font(.system(size: 18, weight: .regular))
        }
    }
    
    private func fieldLabel(_ text: String) -> some View {
        HStack {
            Text(text)
            Spacer()
        }
        .font(.system(size: 18, weight: .semibold))
    }
    
    private var saveButton: some View {
        HStack {
            Spacer()
            Button("Save") { onSave(draft) }
                .font(.system(size: 20, weight: .semibold))
                .foregroundColor(.white)
                .padding(.horizontal, 61.5)
                .padding(.vertical, 16)
                .background(Color(hex: "#0E0E0E"))
                .cornerRadius(8)
        }
    }
    
    // MARK: - Dropdown Overlay
    private var dropdownOverlay: some View {
        Group {
            if dropdownVM.isOpen {
                dropdownBackground
                dropdownContent
            }
        }
    }
    
    private var dropdownBackground: some View {
        Color.black.opacity(0.001)
            .ignoresSafeArea()
            .onTapGesture { dropdownVM.close() }
            .zIndex(998)
    }
    
    private var dropdownContent: some View {
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
        .offset(x: dropdownVM.anchor.minX, y: 8)
        .zIndex(999)
    }
}

#Preview(traits: .landscapeLeft) {
    let vm = DetectConditionViewModel()
    return DetectConditionSheet(vm: vm, onClose: {})
}
