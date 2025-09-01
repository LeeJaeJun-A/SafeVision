//
//  CCTVViewModel.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//


import SwiftUI
import AVKit

class CCTVViewModel: ObservableObject {
    @Published var players: [AVPlayer] = []
    
    private let videoFiles = ["liveCam1.mp4", "liveCam2.mp4", "cctv3.mp4", "cctv4.mp4"]
    
    func loadVideos() {
        var loadedPlayers: [AVPlayer] = []
        
        for name in videoFiles {
            let parts = name.split(separator: ".")
            guard parts.count == 2 else { continue }
            
            let fileName = String(parts[0])
            let fileExtension = String(parts[1])
            
            if let url = Bundle.main.url(forResource: fileName, withExtension: fileExtension) {
                let player = AVPlayer(url: url)
                player.isMuted = true
                player.play()
                loadedPlayers.append(player)
            }
        }
        
        self.players = loadedPlayers
    }
    
    
    
    
    
}
