//
//  SSEManager.swift
//  SafeVision
//
//  Created by KimDogyung on 8/24/25.
//

import SwiftUI
import Combine

class SSEManager: ObservableObject {
    @Published var receivedEvents: [ServerEvent] = []
    @Published var isConnected: Bool = false
    
    private let sseService: SSEServiceProtocol = AlamofireSSEService.shared
    private var cancellables = Set<AnyCancellable>()

    init() {
        subscribeToEvents()
    }
    
    // MARK: - Public Methods
    
    func connect() {
        // ✅ 서비스에 경로만 전달합니다.
        let sseEndpoint = "/api/v1/sse/alerts"
        sseService.connect(to: sseEndpoint)
        // isConnected 상태는 subscribeToEvents 클로저에서 업데이트됩니다.
    }
    
    func disconnect() {
        sseService.disconnect()
    }
    
    // MARK: - Private Methods
    
    private func subscribeToEvents() {
        sseService.eventPublisher
            .sink(receiveCompletion: { [weak self] completion in
                switch completion {
                case .finished:
                    print("ViewModel: Subscription finished.")
                case .failure(let error):
                    print("🚨 ViewModel: Subscription failed with error: \(error.localizedDescription)")
                }
                self?.isConnected = false
            }, receiveValue: { [weak self] newEvent in
                print("📦 ViewModel: Received new event - \(newEvent.message)")
                self?.receivedEvents.insert(newEvent, at: 0)
                self?.isConnected = true // ✅ 연결 성공 시 상태 업데이트
            })
            .store(in: &cancellables)
    }
}
