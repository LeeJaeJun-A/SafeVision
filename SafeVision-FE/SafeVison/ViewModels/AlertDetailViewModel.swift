//
//  AlertDetailViewModel.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import SwiftUI
import AVKit

class AlertDetailViewModel: ObservableObject {
    @Published var detectPlayer: AVPlayer? = nil
    @Published var streamPlayer: AVPlayer? = nil
    @Published var isDownloading: Bool = false
    @Published var downloadError: String?
    
    @Published var isUpdatingStatus: Bool = false
    @Published var statusUpdateError: String?
    
    @Published var camTitle: String = "Cam 3"
    
    private var isLocalVideo: Bool = false
    
    // ✅ 메모리 누수를 방지하기 위해 observer를 저장할 프로퍼티
    private var playerLooperObserver: NSObjectProtocol?
    private var streamPlayerLooperObserver: NSObjectProtocol?
    
    deinit {
        if let observer = playerLooperObserver {
            NotificationCenter.default.removeObserver(observer)
        }
        if let observer = streamPlayerLooperObserver {
            NotificationCenter.default.removeObserver(observer)
        }
    }
    
    private let networkService = NetworkService()
    
    func loadVideo(alert: Alert) {
        
        if alert.videoClipPath.contains("cctv")  {
            isLocalVideo = true
            loadLocalVideo(byFileName: alert.videoClipPath)
        } else {
            isLocalVideo = false
            loadVideoFromAPI(alertID: alert.id)
        }
    }
    
    func loadVideoFromAPI(alertID: String) {
        isDownloading = true // 다운로드 시작 상태로 변경
        downloadError = nil
        
        networkService.downloadAlertVideo(id: alertID) { [weak self] result in
            DispatchQueue.main.async {
                self?.isDownloading = false // 다운로드 완료
                
                switch result {
                case .success(let fileURL):
                    // ✅ 다운로드된 파일의 URL로 AVPlayer를 생성합니다.
                    self?.detectPlayer = AVPlayer(url: fileURL)
                    self?.play()
                case .failure(let error):
                    // ✅ 다운로드 실패 시 에러 메시지를 저장합니다.
                    self?.downloadError = "비디오 다운로드 실패: \(error.localizedDescription)"
                    print("❌ \(self?.downloadError ?? "알 수 없는 에러")")
                }
            }
        }
    }
    
    func loadLocalVideo(byFileName name: String) {
       // 파일 이름과 확장자 분리
        let components = name.split(separator: ".").map(String.init)
        guard components.count == 2,
              let fileName = components.first,
              let fileExtension = components.last else {
            print("잘못된 파일 이름 형식입니다: \(name)")
            return
        }
        
        // 메인 번들에서 비디오 파일의 URL을 찾기
        guard let url = Bundle.main.url(forResource: fileName, withExtension: fileExtension) else {
            print("메인 번들에서 비디오 파일을 찾을 수 없습니다: \(name)")
            return
        }
        
        // 찾은 URL로 AVPlayer를 생성합니다.
        detectPlayer = AVPlayer(url: url)
        setupPlayerLooping(player: detectPlayer, observer: &playerLooperObserver)
    }
    
    
    func startLiveCctv(alert: Alert) {
        
        if alert.videoClipPath.contains("cctv")  {
            guard let url = Bundle.main.url(forResource: "liveCCTV", withExtension: "mp4") else {
                print("메인 번들에서 비디오 파일을 찾을 수 없습니다: ")
                return
            }
            streamPlayer = AVPlayer(url: url)
        } else {
            
            if alert.ruleType == "collision_risk" {
                guard let url = Bundle.main.url(forResource: "liveCam1", withExtension: "mp4") else {
                    print("메인 번들에서 비디오 파일을 찾을 수 없습니다: ")
                    return
                }
                camTitle = "Cam 1"
                streamPlayer = AVPlayer(url: url)
            } else {
                guard let url = Bundle.main.url(forResource: "liveCam2", withExtension: "mp4") else {
                    print("메인 번들에서 비디오 파일을 찾을 수 없습니다: ")
                    return
                }
                camTitle = "Cam 2"
                streamPlayer = AVPlayer(url: url)
            }
        }
        setupPlayerLooping(player: streamPlayer, observer: &streamPlayerLooperObserver)
        
    }
    
    
//    func loadVideo(from url: URL) {
//        detectPlayer = AVPlayer(url: url)
//    }
    
//    func loadVideo(from data: Data) {
//        let tempDir = FileManager.default.temporaryDirectory
//        let fileURL = tempDir.appendingPathComponent("tempVideo.mp4")
//        do {
//            try data.write(to: fileURL)
//            player = AVPlayer(url: fileURL)
//        } catch {
//            print("Error saving temp video:", error)
//        }
//    }
    
    func play() {
        detectPlayer?.play()
        streamPlayer?.play()
    }
    
    func pause() {
        detectPlayer?.pause()
        streamPlayer?.pause()
    }
    
    private func setupPlayerLooping(player: AVPlayer?, observer: inout NSObjectProtocol?) {
        guard let playerItem = player?.currentItem else { return }
        
        observer = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: playerItem,
            queue: .main
        ) { _ in
            player?.seek(to: .zero)
            player?.play()
        }
    }
    
    func markAlertAsProcessing(alert: Alert, completion: @escaping (Bool) -> Void = { _ in }) {
        // 이미 processing 상태이면 API 호출하지 않음
        guard alert.makeStringStatus != "In Progress" && alert.status != "Resolved" else {
            print("ℹ️ Alert는 이미 처리 중이거나 완료된 상태입니다: \(alert.status)")
            completion(true)
            return
        }
        
        isUpdatingStatus = true
        statusUpdateError = nil
        
        networkService.markAlertAsProcessing(id: alert.id) { [weak self] result in
            DispatchQueue.main.async {
                self?.isUpdatingStatus = false
                
                switch result {
                case .success:
                    print("✅ Alert \(alert.id)를 processing 상태로 변경 완료")
                    // 현재 알림의 상태를 업데이트
                    
                    completion(true)
                    
                case .failure(let error):
                    self?.statusUpdateError = "상태 업데이트 실패: \(error.localizedDescription)"
                    print("❌ Processing 상태 변경 실패: \(error.localizedDescription)")
                    completion(false)
                }
            }
        }
    }
    
    func resolveAlert(id: String, completion: @escaping (Bool) -> Void) {
        networkService.resolveAlert(id: id) { result in
            DispatchQueue.main.async {
                switch result {
                case .success:
                    print("✅ Alert \(id) resolved successfully.")
                    completion(true) // 성공했음을 View에 알립니다.
                case .failure(let error):
                    print("❌ Failed to resolve alert: \(error.localizedDescription)")
                    completion(false) // 실패했음을 View에 알립니다.
                }
            }
        }
    }
}
