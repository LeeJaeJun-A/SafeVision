//
//  NavigationManager.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import SwiftUI

enum Destination: Hashable {
    case home
    case detail(alert: Alert)
    case cctv
}

final class NavigationManager: ObservableObject {
    @Published var path = NavigationPath()
    
    func push(_ destination: Destination) {
        path.append(destination)
    }
    
    func pop() {
        path.removeLast()
    }
    
    func popToRoot() {
        path.removeLast(path.count)
    }
}
