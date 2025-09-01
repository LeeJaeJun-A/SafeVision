//
//  HomeView.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import SwiftUI
import UIKit

private struct RectPreferenceKey: PreferenceKey {
    static var defaultValue: CGRect = .zero
    static func reduce(value: inout CGRect, nextValue: () -> CGRect) {
        let next = nextValue()
        if next != .zero { value = next }
    }
}

private extension View {
    func readFrame(in space: CoordinateSpace = .global, onChange: @escaping (CGRect) -> Void) -> some View {
        background(
            GeometryReader { geo in
                Color.clear
                    .preference(key: RectPreferenceKey.self, value: geo.frame(in: space))
            }
        )
        .onPreferenceChange(RectPreferenceKey.self, perform: onChange)
    }
}

struct HomeView: View {
    @ObservedObject var vm: HomeViewModel
    @EnvironmentObject var navigationManager: NavigationManager
    @EnvironmentObject var sseManager: SSEManager

    @State private var showDetectSheet: Bool = false
    @State private var alertSectionFrame: CGRect = .zero
    @State private var containerSize: CGSize = .zero
    @StateObject private var detectVM = DetectConditionViewModel()
    
    var body: some View {
        // ✅ GeometryReader를 ZStack으로 감싸고, ZStack의 자식으로 모든 뷰를 배치
        GeometryReader { proxy in
            let size = proxy.size
            ZStack(alignment: .topLeading) {
                // ✅ 메인 콘텐츠 (배경, 헤더, 섹션 등)
                VStack(spacing: 0) {
                    header
                        .padding(.bottom, 42)
                    
                    HStack(alignment: .top, spacing: 40) {
                        alertsSection
                        alertSettingSection
                            .readFrame(in: .global) { rect in
                                alertSectionFrame = rect
                            }
                    }
                    .appPadding()
                    
                    Spacer()
                }
                .background(Color.mainBackground.ignoresSafeArea())
                .onAppear {
                    vm.startFetchingAlerts()
                    containerSize = size
                }
                .onDisappear {
                    vm.stopFetchingAlerts()
                }
                .onChange(of: size) { _, new in
                    containerSize = new
                }
                
                // ✅ ZStack의 두 번째 자식으로 모달 뷰를 오버레이
                if showDetectSheet {
                    // Dimmed scrim that does not move layout
                    Color.black.opacity(0.3)
                        .ignoresSafeArea()
                        .onTapGesture { withAnimation(.easeOut(duration: 0.2)) { showDetectSheet = false } }
                    
                    // Constrained modal sized to ~3/5 of the page height, width aligned to alert settings section
                    let modalWidth = alertSectionFrame.width
                    let modalHeight = UIScreen.main.bounds.height * 0.8
                    
                    DetectConditionSheet(vm: detectVM, onClose: { withAnimation(.easeOut(duration: 0.2)) { showDetectSheet = false } })
                        .frame(width: modalWidth, height: modalHeight, alignment: .topLeading)
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(Color.white)
                                .shadow(radius: 12)
                        )
                        .offset(x: alertSectionFrame.minX, y: alertSectionFrame.minY - modalHeight/2)
                        .transition(.scale(scale: 0.98).combined(with: .opacity))
                }
            }
            .coordinateSpace(name: "container")
            .toolbar(.hidden, for: .navigationBar)
        }
    }
    
    
    private var logo: some View {
        Image("logo-image")
    }
    
    private var companyLogo: some View {
        Text("HYUNDAI E&C")
            .font(.system(size: 20, weight: .semibold))
            .foregroundStyle(.white)
    }
    
    private var constructionLocation: some View {
        Text("Pohang-si Dongbin Cultural Platform\nNew Building Construction")
            .font(.system(size: 38, weight: .bold))
            .foregroundStyle(.white)
    }
    
    private var address: some View {
        HStack(spacing: 6) {
            Image("BiCurrentLocation")
                .resizable()
                .renderingMode(.template)
                .frame(width: 24, height: 24)
                .foregroundStyle(Color(hex: "#9D9D9D"))
            
            Text("78, Seonchak-ro, Buk-gu, Pohang-si, Gyeongsangbuk-do, Republic of Korea")
                .font(.system(size: 15))
                .foregroundStyle(Color(hex: "#9D9D9D"))
        }
    }
    
    private var header: some View {
        VStack(spacing: 0) {
            logo
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.bottom, 25)
            
            companyLogo
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.bottom, 4)
            
            constructionLocation
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.bottom, 25)
            
            address
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .frame(maxWidth: .infinity)
        .appPadding()
        .padding(.top, 43)
        .padding(.bottom, 49)
        .background {
            ZStack {
                LinearGradient(
                    gradient: Gradient(stops: [
                        .init(color: Color(hex: "#0E0E0E"), location: 0.0),
                        .init(color: Color(hex: "#252468"), location: 0.85),
                        .init(color: Color(hex: "#252468"), location: 1.0)
                    ]),
                    startPoint: .leading,
                    endPoint: .trailing
                )
                
                EllipticalGradient(
                    stops: [
                        .init(color: Color(hex: "#252468"), location: 0.0),
                        .init(color: Color(hex: "#252468").opacity(0), location: 1.0)
                    ],
                    center: .bottomTrailing
                )
            }
            .ignoresSafeArea(.container, edges: .top)
        }
    }
    
    private var alertsSectionHeader: some View {
        HStack(spacing: 8) {
            Button(
                action: {
                    vm.selectFilter(.all)
                },
                label: {
                    Text("All Alerts")
                }
            )
            .buttonStyle(AlertsButtonStyle(isSelected: vm.selectedFilter == .all))
            
            Button(
                action: {
                    vm.selectFilter(.unprocessed)
                },
                label: {
                    Text("Unconfirmed")
                }
            )
            .buttonStyle(AlertsButtonStyle(isSelected: vm.selectedFilter == .unprocessed))
            
            Button(
                action: {
                    vm.selectFilter(.inProgress)
                },
                label: {
                    Text("In Progress")
                }
            )
            .buttonStyle(AlertsButtonStyle(isSelected: vm.selectedFilter == .inProgress))
            
            Button(
                action: {
                    vm.selectFilter(.resolved)
                },
                label: {
                    Text("Resolved")
                }
            )
            .buttonStyle(AlertsButtonStyle(isSelected: vm.selectedFilter == .resolved))
        }
    }
    
    
    private func dangerStatusBar(danger: String) -> some View {
        var numberOfBars: Int
        var barColor: Color
        var text: String
        
        switch danger {
        case "critical":
            numberOfBars = 4
            barColor = Color(hex: "#F94C4C")
            text = "Critical"
        case "high":
            numberOfBars = 3
            barColor = Color(hex: "#FF9945")
            text = "High"
        case "medium":
            numberOfBars = 2
            barColor = Color(hex: "#FFD651")
            text = "Medium"
        case "low":
            numberOfBars = 1
            barColor = Color(hex: "#5AEE7F")
            text = "Low"
        default:
            numberOfBars = 0
            barColor = .clear
            text = ""
        }
        
        return VStack(spacing: 4) {
            HStack(spacing: 8) {
                // ✅ numberOfBars가 5까지 가능하므로, 0..<5로 수정
                ForEach(0..<4, id: \.self) { bar in
                    Rectangle()
                        .fill(bar < numberOfBars ? barColor : Color(hex: "#D9D9D9"))
                        .frame(width: 12, height: 36)
                        .cornerRadius(3)
                }
            }
            
            Text(text)
                .font(.system(size: 14))
                .foregroundStyle(barColor)
        }
    }
    
//    private func makeStringStatus(status: String) -> String {
//        switch status {
//        case "resolved":
//            return "Resolved"
//        case "unprocessed":
//            return "Unconfirmed"
//        case "in_progress":
//            return "In Progress"
//        case "completed":
//            return "Resolved"
//        default:
//            return ""
//        }
//    }
//    
    private func makeAlertCard(alert: Alert) -> some View {
        HStack(spacing: 0){
            VStack(spacing: 0) {
                
                Text(alert.summary)
                    .font(.system(size: 20, weight: .semibold))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.bottom, 8)
                
                Text(alert.formattedCreatedAt)
                    .font(.system(size: 18))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.bottom, 28)
                
                Text(alert.makeStringStatus)
                    .font(.system(size: 18))
                    .foregroundStyle(alert.status == "unprocessed" ? .white : .black)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 8)
                    .background(alert.status == "unprocessed" ? .black : Color(hex: "#F2F2F2"))
                    .cornerRadius(32)
                    .overlay(
                        RoundedRectangle(cornerRadius: 32)
                            .stroke(
                                alert.status == "unprocessed" ? .clear : .black,
                                lineWidth: 1
                            )
                    )
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            
            Spacer()
            
            
            dangerStatusBar(danger: alert.severity)
        }
        .frame(minWidth: 540)
        .padding(.leading, 24)
        .padding(.trailing, 40)
        .padding(.top, 20)
        .padding(.bottom, 24)
        .background(.white)
        .cornerRadius(8)
    }
    
    
    
    
    private var alertsSection: some View {
        
        VStack(alignment: .leading, spacing: 0) {
            alertsSectionHeader
                .padding(.bottom, 16)
                .frame(maxWidth: .infinity, alignment: .leading)
            
            ScrollView(showsIndicators: false) {
                ForEach( vm.filteredAlerts ) { alert in
                    makeAlertCard(alert: alert)
                        .padding(.bottom, 16)
                        .onTapGesture {
                            navigationManager.push(.detail(alert: alert))
                        }
                }
            }
        }
    }
    
    
    private var rulePreview: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack{
                Text("Collision")
                    .font(.system(size: 18, weight: .regular))
                Spacer()
                Text("3")
                    .font(.system(size: 14, weight: .regular))
                    .foregroundColor(.gray)
            }
            .padding(20)
            .frame(height: 60)
            .border(Color(hex: "#EAECF4"), width: 1)
            .cornerRadius(6)
            
            HStack{
                Text("Fall")
                    .font(.system(size: 18, weight: .regular))
                Spacer()
                Text("5")
                    .font(.system(size: 14, weight: .regular))
                    .foregroundColor(.gray)
            }
            .padding(20)
            .frame(height: 60)
            .border(Color(hex: "#EAECF4"), width: 1)
            .cornerRadius(6)
            .padding(.top, 16)
            
            HStack{
                Spacer()
                Text("More Rules")
                    .font(.system(size: 16, weight: .regular))
                    .foregroundColor(.gray)
//                Label("7 More", systemImage: "plus")
//                    .foregroundColor(.gray)
                Spacer()
            }
            .padding(.top, 16)
        }
        .frame(maxHeight: UIScreen.main.bounds.height - 700)
        .padding(.vertical, 28)
        .background(.white)
        .cornerRadius(8)
    }
    
    
    private var alertSettingSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            
            VStack{
                HStack(spacing: 0) {
                    Text("Alerts Settings")
                        .font(.system(size: 22, weight: .medium))
                    
                    Spacer()
                    
                    Button(action: {
                        withAnimation(.easeOut(duration: 0.2)) { showDetectSheet = true }
                    }) {
                        Image("arrow")
                            .frame(width: 20, height: 20)
                    }
                }
                .padding(.bottom, 20)
                
                rulePreview
            }
            .padding(24)
            .background(Color(.white))
            .cornerRadius(8)
                                    
            Button(
                action: {
                    navigationManager.push(.cctv)
                },
                label: {
                    HStack(spacing: 8) {
                        Image("cam")
                            .frame(width: 20, height: 20)
                        
                        Text("View CCTV")
                            .font(.system(size: 22, weight: .semibold))
                            .foregroundStyle(.white)
                    }
                    .frame(minWidth: 300, maxWidth: .infinity)
                    .padding(.vertical, 43)
                    .background {
                        ZStack {
                            LinearGradient(
                                gradient: Gradient(stops: [
                                    .init(color: Color(hex: "#0E0E0E"), location: 0.0),
                                    .init(color: Color(hex: "#0E0E0E"), location: 0.97),
                                    .init(color: Color(hex: "#252468"), location: 1.0)
                                ]),
                                startPoint: .trailing,
                                endPoint: .leading
                            )
                            
                            EllipticalGradient(
                                stops: [
                                    .init(color: Color(hex: "#252468"), location: 0.0),
                                    .init(color: Color(hex: "#252468").opacity(0), location: 1.0)
                                ],
                                center: .bottomLeading
                            )
                        }
                    }
                    .cornerRadius(8)
                }
            )
            .padding(.top, 20)
        }
    }
    
    
}


struct AlertsButtonStyle: ButtonStyle {
    var isSelected: Bool
    func makeBody(configuration: Configuration) -> some View {
        
        configuration.label
            .font(.system(size: 18))
            .foregroundColor(isSelected ? Color.white : Color.textGray)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(isSelected ? Color.black : Color.white)
            .cornerRadius(8)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.easeOut(duration: 0.2), value: configuration.isPressed)
    }
}


#Preview("Landscape Preview", traits: .landscapeLeft) {
    HomeView(vm: HomeViewModel())
        .environmentObject(NavigationManager())
}
