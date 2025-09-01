//
//  RootView.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import SwiftUI

struct RootView: View {
    @StateObject private var navigationManager = NavigationManager()
    @StateObject private var sseManager = SSEManager()
    @StateObject private var homeViewModel = HomeViewModel()
    @StateObject private var alertDetailViewModel = AlertDetailViewModel()
    @StateObject private var cctvViewModel = CCTVViewModel()
    
    var body: some View {
        NavigationStack(path: $navigationManager.path) {
            HomeView(vm: homeViewModel)
                .navigationDestination(for: Destination.self) { destination in
                    switch destination {
                    case .home:
                        HomeView(vm: homeViewModel)
                    case .detail(let alert):
                        AlertDetailView(vm: alertDetailViewModel, alert: alert)
                    case .cctv:
                        CCTVView(vm: cctvViewModel)
                    }
                }
        }
        .environmentObject(navigationManager)
        .environmentObject(sseManager)
    }
}
