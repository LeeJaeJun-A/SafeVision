//
//  AlertDetailView.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import SwiftUI
import AVKit


struct AlertDetailView: View {
    @ObservedObject var vm: AlertDetailViewModel
    @EnvironmentObject var navigationManager: NavigationManager
    var alert: Alert
    
    
    var body: some View {
        VStack(spacing: 0) {
            
            HStack(alignment: .center, spacing: 30) {
                leftPanel
                infoPanel
            }
            .padding(.top, 20)
            .padding(.horizontal, 30)
            
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                backButton
                    .padding(.horizontal, 36)
                    .padding(.top, 36)
            }
            
            ToolbarItem(placement: .principal) {
                Text(alert.summary)
                    .font(.system(size: 26, weight: .semibold))
                    .foregroundStyle(.black)
                    .padding(.top, 47)
            }
        }
        .ignoresSafeArea()
        .background(Color(hex:"#EAECF4"))
        .onAppear {
            vm.loadVideo(alert: alert)
            vm.startLiveCctv(alert: alert)
            vm.detectPlayer?.isMuted = true
            vm.play()
            vm.markAlertAsProcessing(alert: alert) { success in
                if success {
                    print("✅ Alert가 processing 상태로 변경되었습니다.")
                }
            }
        }
    }
    
    
    private var backButton: some View {
        Button(
            action: {
                navigationManager.pop()
            },
            label: {
                Image(systemName: "arrow.left")
                    .background(
                        Circle()
                            .fill(.white)
                            .frame(width: 60, height: 60)
                    )
                    .foregroundColor(.black)
            }
        )
    }
    
    //    private var title: some View {
    //        Text(alert.title)
    //            .font(.system(size: 32, weight: .semibold))
    //            .foregroundStyle(.black)
    //    }
    
    
    private var leftPanel: some View {
        VStack(spacing: 20) {
            // 상단 비디오 플레이어 뷰 (재생 버튼 포함)
            detectVideoView
            
            // 하단 라이브 캠 뷰 (빨간색 레이블 포함)
            streamVideoView
        }
        .padding(.top, 50)
    }
    
    private var detectVideoView: some View {
        ZStack {
            // 비디오 플레이어
            if let player = vm.detectPlayer {
                VideoPlayer(player: player)
                    .frame(height: 280)
            } else {
                VideoPlayer(player: nil)
                    .frame(height: 280)
            }
        }
        .cornerRadius(12)
    }
    
    private var streamVideoView: some View {
        ZStack(alignment: .topLeading) {
            // 비디오 플레이어
            if let player = vm.streamPlayer {
                VideoPlayer(player: player)
                    .frame(height: 280)
            } else {
                VideoPlayer(player: nil)
                    .frame(height: 280)
            }
            
            // 'Live Cam' 레이블
            Text("Live \(vm.camTitle)")
                .font(.system(size: 14, weight: .bold))
                .foregroundStyle(.white)
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(Color(hex: "#F44336"))
                .cornerRadius(5)
                .padding(10)
        }
        .cornerRadius(12)
    }
    
    private var infoPanel: some View {
        VStack(spacing: 20) {
            Text("Info")
                .font(.system(size: 20, weight: .semibold))
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.bottom, 40)
            
            VStack(spacing: 16) {
                InfoRow(key: "Time", value: alert.formattedCreatedAt)
                Divider()
                InfoRow(key: "Risk Level", value: alert.capitalizedSeverity)
                Divider()
                InfoRow(key: "Camera ID", value: vm.camTitle)
                Divider()
                InfoRow(key: "Status", value: alert.makeStringStatus)
            }
            .padding(.horizontal, 10)
            
            Spacer()
            
            buttons
                .padding(.bottom, 46)
            
        }
        .frame(width: 434, height: 470)
        .padding(.top, 40)
        .padding(.horizontal, 32)
        .background(
            Color.white
                .cornerRadius(8)
        )
    }
    
    private var buttons: some View {
        HStack(spacing: 20) {
//            Button("Acknowledge") {
//                navigationManager.pop()
//            }
//            .font(.system(size: 20, weight: .semibold))
//            .frame(minWidth: 170)
//            .padding(16)
//            .background(Color.white)
//            .foregroundColor(.black)
//            .cornerRadius(8)
//            .overlay(
//                RoundedRectangle(cornerRadius: 8)
//                    .stroke(Color.black, lineWidth: 1)
//            )
            
            Button("Resolve") {
                if alert.status != "resolved" {
                    vm.resolveAlert(id: alert.id) { success in
                        // ✅ API 호출이 성공하면(true) 화면을 이전으로 되돌립니다.
                        if success {
                            navigationManager.pop()
                        }
                    }
                }
            }
            .font(.system(size: 20, weight: .semibold))
            .frame(minWidth: 170)
            .padding(16)
            .background(Color.black)
            .foregroundColor(.white)
            .cornerRadius(8)
        }
    }
    
}


private struct InfoRow: View {
    let key: String
    let value: String
    
    var body: some View {
        HStack(spacing: 62) {
            Text(key)
                .font(.system(size: 20, weight: .semibold))
                .foregroundColor(.black)
                .frame(width: 120, alignment: .leading)
            
            
            
            Text(value)
                .font(.system(size: 20, weight: .regular))
                .foregroundColor(.black)
                .frame(maxWidth: .infinity, alignment: .leading)
            
            
        }
    }
}

#Preview (traits: .landscapeLeft){
    AlertDetailView(vm: AlertDetailViewModel(), alert: Alert.mocks[0])
        .environmentObject(NavigationManager())
}
