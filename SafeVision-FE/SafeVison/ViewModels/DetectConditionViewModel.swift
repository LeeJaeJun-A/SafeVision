//
//  DetectConditionViewModel.swift
//  SafeVision
//
//  Created by Nike on 8/23/25.
//

import Foundation
import SwiftUI
import Combine
import Alamofire

@MainActor
final class DetectConditionViewModel: ObservableObject {
    
    @Published var serverConditions: [DetectCondition] = []
    @Published var isLoadingRules: Bool = false
    @Published var rulesErrorMessage: String? = nil
//    @Published var conditions: [DetectCondition] = [
//        DetectCondition(
//            id: UUID(),
//            name: "급락 감지",
//            type: .fall,
//            description: "카메라 프레임 내 사람이 급격히 수직 낙하",
//            rate: 4,
//            durationSec: 3   // 3초
//        ),
//        DetectCondition(
//            id: UUID(),
//            name: "충돌 위험",
//            type: .collision,
//            description: "두 객체의 이동 벡터가 수렴(상호 충돌 위험)",
//            rate: 2,
//            durationSec: 2
//        ),
//        DetectCondition(
//            id: UUID(),
//            name: "과밀 구간",
//            type: .density,
//            description: "ROI 내 인원 밀집도 임계치 초과(> 6명/㎡)",
//            rate: 1,
//            durationSec: 10
//        ),
//        DetectCondition(
//            id: UUID(),
//            name: "출입금지 침범",
//            type: .restricted,
//            description: "출입금지 구역 경계선 침범",
//            rate: 2,
//            durationSec: 1
//        ),
//        DetectCondition(
//            id: UUID(),
//            name: "미분류 이상",
//            type: .density, // ← 기존에 .undefined였다면 .unknown으로 바꾸세요
//            description: "모델이 분류하지 못한 이상 패턴",
//            rate: 3,
//            durationSec: 5
//        ),
//        
//        DetectCondition(
//            id: UUID(),
//            name: "낙상 후 무반응",
//            type: .fall,
//            description: "낙상 후 3초 이상 움직임 없음",
//            rate: 4,
//            durationSec: 3
//        ),
//        DetectCondition(
//            id: UUID(),
//            name: "차량-보행자 근접",
//            type: .collision,
//            description: "차량-보행자 근접 거리 < 0.5m",
//            rate: 3,
//            durationSec: 1
//        ),
//        DetectCondition(
//            id: UUID(),
//            name: "대피구 정체",
//            type: .density,
//            description: "대피구 통로 정체 감지",
//            rate: 1,
//            durationSec: 30
//        ),
//        DetectCondition(
//            id: UUID(),
//            name: "야간 무단출입",
//            type: .restricted,
//            description: "야간 시간대 공사장 무단 출입",
//            rate: 2,
//            durationSec: 2
//        )
//    ]
    
    private let network = NetworkService()
    
    func loadRulesAsConditions() {
        guard !isLoadingRules else { return }
        isLoadingRules = true
        rulesErrorMessage = nil
        
        network.fetchRulesResponse { [weak self] result in
            guard let self = self else { return }
            self.isLoadingRules = false
            
            switch result {
            case .success(let rulesResponse):
                // 서버에서 받은 Rule → DetectCondition 변환
                let mapped = rulesResponse.data.map { DetectCondition(from: $0) }
                self.serverConditions = mapped
                
                print("✅ 서버 Rules → DetectCondition 변환 완료 (\(mapped.count)건)")
                // 디버그 출력(첫 3건만 예시)
                for c in mapped.prefix(3) {
                    print(" - \(c.name) / \(c.type.rawValue) / rate=\(c.rate) / dur=\(c.durationSec)s")
                }
                
            case .failure(let error):
                self.rulesErrorMessage = error.localizedDescription
                print("❌ Rules 불러오기 실패: \(error.localizedDescription)")
            }
        }
    }
    
    private func severity(from rate: Int) -> String {
        switch rate {
        case let r where r >= 4: return "critical"
        case 3: return "high"
        case 2: return "medium"
        case 1: return "low"
        default: return "low"
        }
    }
    
    func loadRules() {
        guard !isLoadingRules else { return }
        isLoadingRules = true
        rulesErrorMessage = nil

        network.fetchRulesResponse { [weak self] result in
            guard let self = self else { return }
            self.isLoadingRules = false

            switch result {
            case .success(let resp):
                print("✅ Rules 불러옴: total=\(resp.totalCount)")
                // 서버 Rule → 앱 DetectCondition 매핑 (확장 구현 필요: DetectCondition(from: Rule))
                self.serverConditions = resp.data.map { DetectCondition(from: $0) }
            case .failure(let error):
                print("❌ Rules 불러오기 실패: \(error.localizedDescription)")
                self.rulesErrorMessage = error.localizedDescription
            }
        }
    }
    
    // MARK: [NEW] DetectCondition → RuleRequest 변환 (서버 타입 매핑 포함)
    private func makeRuleRequest(from cond: DetectCondition) throws -> RuleRequest {
        guard let serverType = cond.type.serverRuleType else {
            // 서버 타입이 매핑되지 않은 경우 (unknown 등)
            let msg = "❌ 매핑 실패: '\(cond.type.rawValue)'는 서버 type으로 매핑되지 않음"
            print(msg)
            throw NSError(domain: "RuleTypeMapping", code: -1, userInfo: [NSLocalizedDescriptionKey: msg])
        }
        
        return RuleRequest(
            name: cond.name.isEmpty ? cond.type.rawValue : cond.name,
            type: serverType.rawValue,                 // ← 서버 요구 사항 반영
            severity: severity(from: cond.rate),
            description: cond.description,
            duration: cond.durationSec
        )
    }
    
    func postCondition(_ cond: DetectCondition,
                       completion: @escaping (Result<String, AFError>) -> Void) {
        do {
            let body = try makeRuleRequest(from: cond)
            
            //                // 터미널 확인용 로그
            //                print("📤 POST /api/v1/rules/user-friendly")
            //                print("   - name: \(body.name)")
            //                print("   - type: \(body.type)")
            //                print("   - severity: \(body.severity)")
            //                print("   - description: \(body.description)")
            //                print("   - duration: \(body.duration) sec")
            
            network.createUserFriendlyRule(request: body) { result in
                switch result {
                case .success(let resp):
                    print("✅ 단일 전송 성공:\n\(resp)")
                    completion(.success(resp))
                case .failure(let err):
                    print("❌ 단일 전송 실패: \(err.localizedDescription)")
                    completion(.failure(err))
                }
            }
        } catch {
            print("🚨 전송 취소(사전 오류): \(error.localizedDescription)")
            completion(.failure(AFError.createURLRequestFailed(error: error)))
        }
    }
    
    func deleteServerCondition(_ cond: DetectCondition) {
        guard let ruleId = cond.id else {
            print("❌ 삭제 실패: serverId가 없습니다.")
            return
        }
        
        // UI에 로딩을 보여주고 싶다면 isLoadingRules를 재사용해도 됩니다.
        network.deleteRule(id: ruleId) { [weak self] result in
            switch result {
            case .success:
                print("✅ 규칙 삭제 성공: \(ruleId)")
                // 1) 서버 최신 상태를 다시 불러오거나
                self?.loadRulesAsConditions()
                // 2) 또는 로컬에서 즉시 제거하려면 아래 사용:
                // self?.serverConditions.removeAll { $0.serverId == ruleId }
            case .failure(let err):
                print("❌ 규칙 삭제 실패: \(err.localizedDescription)")
            }
        }
    }
    
//    func insert(_ condition: DetectCondition) {
//        if let idx = conditions.firstIndex(where: { $0.id == condition.id }) {
//            conditions[idx] = condition
//        } else {
//            conditions.append(condition)
//        }
//    }
//    
//    func delete(at offsets: IndexSet) {
//        conditions.remove(atOffsets: offsets)
//    }
//    
//    func delete(id: UUID) {
//        conditions.removeAll { $0.id == id }
//    }
}
