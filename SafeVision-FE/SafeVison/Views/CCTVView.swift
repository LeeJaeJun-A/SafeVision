//
//  CCTVView.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import SwiftUI
import AVKit

struct CCTVView: View {
    
    @StateObject var vm: CCTVViewModel
    @EnvironmentObject var navigationManager: NavigationManager
    
    var body: some View {
        ZStack(alignment: .topTrailing) {
            
            // 2x2 그리드
            Grid(horizontalSpacing: 0, verticalSpacing: 0) {
                ForEach(0..<2, id: \.self) { row in
                    GridRow {
                        ForEach(0..<2, id: \.self) { col in
                            let index = row * 2 + col
                            videoCell(for: index)
                        }
                    }
                }
            }
            .background(.black)
            .navigationBarBackButtonHidden(true)
            
            // 닫기 버튼
            closeButton
        }
        .onAppear {
            vm.loadVideos()
        }
    }
}

extension CCTVView {
    
    /// 하나의 CCTV 셀
    private func videoCell(for index: Int) -> some View {
        ZStack(alignment: .topLeading) {
            if vm.players.indices.contains(index) {
                VideoPlayer(player: vm.players[index])
                    .overlay(Rectangle().stroke(Color.white, lineWidth: 1))
            } else {
                Rectangle()
                    .fill(Color.gray)
                    .overlay(Rectangle().stroke(Color.white, lineWidth: 1))
            }
            
            tagLabel(for: index+1)
        }
    }
    
    /// 좌상단 카메라 태그
    private func tagLabel(for index: Int) -> some View {
        Text("Cam \(index)")
            .font(.system(size: 14))
            .foregroundColor(.black)
            .padding(EdgeInsets(top: 4, leading: 8, bottom: 4, trailing: 8))
            .background(Color.white)
            .cornerRadius(6)
            .padding(12)
    }
    
    /// 우상단 닫기 버튼
    private var closeButton: some View {
        Button(action: {
            navigationManager.pop()
        }) {
            ZStack {
                Rectangle()
                    .foregroundColor(.clear)
                    .frame(width: 54, height: 54)
                    .background(.black.opacity(0.3))
                    .cornerRadius(56)
                
                Image(systemName: "xmark")
                    .foregroundColor(.white)
                    .font(.system(size: 20, weight: .semibold))
            }
        }
        .padding(24)
    }
}


#Preview {
    CCTVView(vm: CCTVViewModel())
        .environmentObject(NavigationManager())
}


