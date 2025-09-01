//
//  RuleRequest.swift
//  SafeVision
//
//  Created by KimDogyung on 8/24/25.
//

import Foundation

struct RuleRequest: Encodable {
    let name: String
    let type: String
    let severity: String
    let description: String
    let duration: Int
}
