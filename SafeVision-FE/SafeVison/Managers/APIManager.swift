//
//  APIManager.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import Foundation

func getAPIKey() -> String {
    guard let urlString = Bundle.main.object(forInfoDictionaryKey: "BASE_URL") as? String else {
        fatalError("BASE_URL not found")
    }
  
    return urlString
}

let apiKey = getAPIKey()
