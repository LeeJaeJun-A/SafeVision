//
//  HomeViewModel.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import SwiftUI
import Combine

enum AlertFilterType {
    case all
    case unprocessed
    case inProgress
    case resolved
}

class HomeViewModel: ObservableObject {

//    @Published var alerts: [MockAlert] = []
    
    @Published var alerts: [Alert] = Alert.mocks
    @Published var selectedFilter: AlertFilterType = .all
    
    var filteredAlerts: [Alert] {
        switch selectedFilter {
        case .all:
            return alerts
        case .unprocessed:
            // Alert의 status가 "unprocessed"인 항목만 필터링
            return alerts.filter { $0.status == "unprocessed" }
        case .inProgress:
            // Alert의 status가 "in_progress"인 항목만 필터링
            return alerts.filter { $0.status == "in_progress" || $0.status == "processing" }
        case .resolved:
            // Alert의 status가 "resolved"인 항목만 필터링
            return alerts.filter { $0.status == "resolved" || $0.status == "complete"}
        }
    }
    
    private let networkService = NetworkService()
    
    // ✅ 타이머와 구독을 관리하기 위한 Cancellable 집합
    private var cancellables = Set<AnyCancellable>()
    
    
    
    // ✅ View에서 필터를 변경할 수 있도록 하는 함수
    func selectFilter(_ filter: AlertFilterType) {
        self.selectedFilter = filter
    }
    
    // ✅ 1초마다 알림 데이터를 가져오기 시작하는 함수
    func startFetchingAlerts() {
        // networkService의 startAlertPolling 함수를 호출하고, 결과를 받습니다.
        networkService.startAlertPolling { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success(let fetchedAlerts):
                    // 성공적으로 데이터를 가져오면 alerts 배열 업데이트
                    self?.alerts = Alert.mocks
                    self?.alerts.insert(contentsOf: fetchedAlerts, at: 0)
                    print("Received \(fetchedAlerts.count) alerts from API.")
                case .failure(let error):
                    // 오류 발생 시 에러 출력
                    print("Failed to fetch alerts: \(error.localizedDescription)")
                    // 필요 시 오류 상태를 UI에 표시할 수 있습니다.
                }
            }
        }
    }
    
    // ✅ 알림 데이터 가져오기를 중지하는 함수
    func stopFetchingAlerts() {
        networkService.stopAlertPolling()
    }
    
    
    
//    func fetchMockAlerts() {
//        alerts = MockAlert.mocks
//    }
    
    
    func checkServerHealth() {
            // networkService 인스턴스를 통해 health check 함수를 호출
        networkService.performHealthCheck()
    }
    
    
    
}
