//
//  ServerEvent.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import Foundation

struct ServerEvent: Decodable, Identifiable {
    let id: UUID
    let message: String
    let timestamp: Date
    
    
    enum CodingKeys: String, CodingKey {
        case message
        case timestamp
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = UUID()
        self.message = try container.decode(String.self, forKey: .message)
        
        let dateDouble = try container.decode(Double.self, forKey: .timestamp)
        self.timestamp = Date(timeIntervalSince1970: dateDouble)
    }
}
