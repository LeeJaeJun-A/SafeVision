//
//  NetworkService.swift
//  SafeVision
//
//  Created by KimDogyung on 8/23/25.
//

import Foundation
import Alamofire
import Combine


public class NetworkService {
    
    // ServerTrustManager를 정의하여 특정 호스트에 대한 인증서 검증을 비활성화합니다.
    private let serverTrustManager: ServerTrustManager
    
    // 커스텀 Session 인스턴스 생성
    private let session: Session
    
    // ✅ 1초마다 요청을 보내기 위한 타이머
    private var pollingTimer: AnyCancellable?
    
    
    public init() {
        // 인증서 유효성 검사를 비활성화할 호스트를 설정
        self.serverTrustManager = ServerTrustManager(
            evaluators: [
                // "your-insecure-domain.com"에 대한 인증서 검증을 건너뛰도록 설정
                "\(apiKey)": DisabledTrustEvaluator()
            ]
        )
        
        // 커스텀 ServerTrustManager를 사용하여 Session 인스턴스 초기화
        self.session = Session(serverTrustManager: self.serverTrustManager)
    }
    
    let endpoint = API.healthCheck
    var healthCheckURL: String {
        return "https://\(apiKey)\(endpoint.path)"
    }
    
    func performHealthCheck() {
        
        self.session.request(healthCheckURL, method: .get)
            .validate(statusCode: 200..<300) // 2xx 상태 코드를 정상으로 간주
            .response { response in
                switch response.result {
                case .success:
                    // 서버가 정상적으로 응답했습니다.
                    if let statusCode = response.response?.statusCode {
                        print("✅ 서버 헬스 체크 성공! 상태 코드: \(statusCode)")
                    } else {
                        print("✅ 서버 헬스 체크 성공! 상태 코드 확인 불가")
                    }
                    
                case .failure(let error):
                    // 요청 실패 (네트워크 오류, 서버 오류 등)
                    print("❌ 서버 헬스 체크 실패: \(error.localizedDescription)")
                    
                    if let statusCode = response.response?.statusCode {
                        print("❌ 실패 상태 코드: \(statusCode)")
                    }
                }
            }
    }
    
    
    // ✅ 1초마다 알림을 가져오는 함수
    func startAlertPolling(completion: @escaping (Result<[Alert], AFError>) -> Void) {
        // 이미 타이머가 실행 중인 경우 중복 방지
        guard pollingTimer == nil else { return }
        
        // 1초마다 이벤트를 발행하는 타이머 생성
        pollingTimer = Timer.publish(every: 1.0, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                // ✅ 타이머가 동작할 때마다 경고 데이터를 가져오는 함수 호출
                self?.fetchAlerts(completion: completion)
            }
    }
    
    func stopAlertPolling() {
        // ✅ 타이머를 취소하여 더 이상 요청이 발생하지 않도록 합니다.
        pollingTimer?.cancel()
        pollingTimer = nil
    }
    
    private func fetchAlerts(completion: @escaping (Result<[Alert], AFError>) -> Void) {
        let alertsEndpoint = API.getAlerts
        let alertsURL = "https://\(apiKey)\(alertsEndpoint.path)"
        
        self.session.request(alertsURL, method: .get)
            .validate() // 2xx 응답이 아니면 실패로 처리
            .responseDecodable(of: [Alert].self) { response in
                switch response.result {
                case .success(let alerts):
                    print("✅ 경고 데이터 가져오기 성공!")
                    
                    completion(.success(alerts))
                case .failure(let error):
                    print("❌ 경고 데이터 가져오기 실패: \(error.localizedDescription)")
                    
                    // ✅ 422 상태 코드가 반환되면 APIError 모델로 디코딩을 시도합니다.
                    if let data = response.data, response.response?.statusCode == 422 {
                        do {
                            let apiError = try JSONDecoder().decode(APIError.self, from: data)
                            print("🚨 422 에러 상세: \(apiError.detail.first?.msg ?? "내용 없음")")
                        } catch {
                            print("🚨 422 에러 디코딩 실패: \(error.localizedDescription)")
                        }
                    }
                    completion(.failure(error))
                }
            }
    }
    
    
    // ✅ 비디오 파일을 다운로드하는 함수
    func downloadAlertVideo(id: String, completion: @escaping (Result<URL, AFError>) -> Void) {
        let endpoint = API.downloadAlertVideo(id: id)
        let downloadURL = "https://\(apiKey)\(endpoint.path)"
        
        // ✅ 다운로드된 파일을 저장할 임시 위치를 설정합니다.
        let destination: DownloadRequest.Destination = { _, _ in
            let temporaryDirectory = FileManager.default.temporaryDirectory
            let fileURL = temporaryDirectory.appendingPathComponent(UUID().uuidString).appendingPathExtension("mp4")
            return (fileURL, [.removePreviousFile, .createIntermediateDirectories])
        }
        
        // ✅ session.download 메서드를 사용하여 파일을 다운로드합니다.
        self.session.download(downloadURL, to: destination)
            .validate()
            .response { response in
                switch response.result {
                case .success(let fileURL):
                    if let fileURL = fileURL {
                        print("✅ 비디오 파일 다운로드 성공: \(fileURL.path)")
                        completion(.success(fileURL))
                    } else {
                        print("❌ 다운로드된 파일 URL을 찾을 수 없습니다.")
                        completion(.failure(AFError.responseValidationFailed(reason: .unacceptableStatusCode(code: 200))))
                    }
                case .failure(let error):
                    print("❌ 비디오 파일 다운로드 실패: \(error.localizedDescription)")
                    completion(.failure(error))
                }
            }
    }
    
    func updateAlertStatus(id: String, status: String, completion: @escaping (Result<Void, AFError>) -> Void) {
        let path = API.resolve(id: id).path
        let urlString = "https://\(apiKey)\(path)"
        
        let parameters: Parameters = ["status": status]
        
        self.session.request(urlString, method: .patch, parameters: parameters, encoding: JSONEncoding.default)
            .validate()
            .response { response in
                switch response.result {
                case .success:
                    print("✅ 알림 ID \(id) 상태를 '\(status)'로 변경 성공!")
                    completion(.success(()))
                case .failure(let error):
                    print("❌ 알림 ID \(id) 상태 변경 실패: \(error.localizedDescription)")
                    
                    // 에러 응답 디버깅
                    if let data = response.data, let responseString = String(data: data, encoding: .utf8) {
                        print("🚨 서버 응답: \(responseString)")
                    }
                    
                    completion(.failure(error))
                }
            }
    }
    
    // ✅ 알림을 "processing" 상태로 변경하는 함수
    func markAlertAsProcessing(id: String, completion: @escaping (Result<Void, AFError>) -> Void) {
        updateAlertStatus(id: id, status: "processing", completion: completion)
    }
    
    // ✅ 기존 resolveAlert 함수를 새로운 updateAlertStatus를 사용하도록 수정
    func resolveAlert(id: String, completion: @escaping (Result<Void, AFError>) -> Void) {
        updateAlertStatus(id: id, status: "completed", completion: completion)
    }
    
    
    //    // MARK: Uploads
    //    // ✅ 비디오 파일을 업로드하는 함수 추가
    //    func uploadVideo(fileURL: URL, completion: @escaping (Result<String, AFError>) -> Void) {
    //        let uploadURL = "https://\(apiKey)\(API.upload.path)"
    //
    //        self.session.upload(multipartFormData: { multipartFormData in
    //            // "file"이라는 이름으로 비디오 파일을 추가
    //            multipartFormData.append(fileURL, withName: "file")
    //        }, to: uploadURL)
    //        .validate() // 2xx 상태 코드를 정상으로 간주
    //        .responseString { response in
    //            switch response.result {
    //            case .success(let value):
    //                print("✅ 비디오 파일 업로드 성공!")
    //                completion(.success(value))
    //            case .failure(let error):
    //                print("❌ 비디오 파일 업로드 실패: \(error.localizedDescription)")
    //
    //                // ✅ 422 에러 응답을 디코딩하여 출력
    //                if let data = response.data, response.response?.statusCode == 422 {
    //                    do {
    //                        let apiError = try JSONDecoder().decode(APIError.self, from: data)
    //                        print("🚨 422 에러 상세: \(apiError.detail.first?.msg ?? "내용 없음")")
    //                    } catch {
    //                        print("🚨 422 에러 디코딩 실패: \(error.localizedDescription)")
    //                    }
    //                }
    //                completion(.failure(error))
    //            }
    //        }
    //    }
    //
    // MARK: - Rules
    
    func fetchRulesResponse(completion: @escaping (Result<RulesResponse, AFError>) -> Void) {
        let endpoint = API.getRules
        let rulesURL = "https://\(apiKey)\(endpoint.path)"
        
        self.session.request(rulesURL, method: .get)
            .validate()
            .responseDecodable(of: RulesResponse.self) { response in
                switch response.result {
                case .success(let rulesResponse):
                    print("✅ 규칙 데이터 가져오기 성공! 총 \(rulesResponse.totalCount)개의 규칙")
                    completion(.success(rulesResponse))
                case .failure(let error):
                    print("❌ 규칙 데이터 가져오기 실패: \(error.localizedDescription)")
                    completion(.failure(error))
                }
            }
    }
    
    
    func createUserFriendlyRule(request: RuleRequest, completion: @escaping (Result<String, AFError>) -> Void) {
        let endpoint = API.createUserFriendlyRule(request: request)
        let urlString = "https://\(apiKey)\(endpoint.path)"
        
        // Alamofire의 request 메서드를 사용하여 POST 요청
        self.session.request(urlString, method: endpoint.method, parameters: request, encoder: JSONParameterEncoder.default)
            .validate()
            .responseString { response in
                switch response.result {
                case .success(let value):
                    print("✅ Rule 생성 성공: \(value)")
                    completion(.success(value))
                case .failure(let error):
                    print("❌ Rule 생성 실패: \(error.localizedDescription)")
                    
                    if let data = response.data, response.response?.statusCode == 422 {
                        do {
                            let apiError = try JSONDecoder().decode(APIError.self, from: data)
                            print("🚨 422 에러 상세: \(apiError.detail.first?.msg ?? "내용 없음")")
                        } catch {
                            print("🚨 422 에러 디코딩 실패: \(error.localizedDescription)")
                        }
                    }
                    completion(.failure(error))
                }
            }
    }
    
    func deleteRule(id: String, completion: @escaping (Result<Void, AFError>) -> Void) {
        let endpoint = API.deleteRule(id: id)
        let urlString = "https://\(apiKey)\(endpoint.path)"
        
        self.session.request(urlString, method: endpoint.method)
            .validate(statusCode: 200..<300)
            .response { response in
                switch response.result {
                case .success:
                    print("✅ 규칙 삭제 성공: \(id)")
                    completion(.success(()))
                case .failure(let error):
                    print("❌ 규칙 삭제 실패: \(error.localizedDescription)")
                    
                    if let data = response.data,
                       let raw = String(data: data, encoding: .utf8) {
                        print("🚨 서버 응답: \(raw)")
                    }
                    
                    completion(.failure(error))
                }
            }
    }
    
    
}



enum API {
    case healthCheck
    case getAlerts
    case resolve(id: String)
    case upload
    case createUserFriendlyRule(request: RuleRequest)
    case downloadAlertVideo(id: String)
    case getRules
    case deleteRule(id: String)
}


extension API {
    
    // HTTP 메서드 (GET, POST 등)
    var method: HTTPMethod {
        switch self {
        case .healthCheck, .getAlerts, .downloadAlertVideo, .getRules:
            return .get
        case .resolve:
            return .patch
        case .upload:
            return .post
        case .createUserFriendlyRule: // ✅ POST 메서드 추가
            return .post
        case .deleteRule:
            return .delete
        }
    }
    
    // 엔드포인트 경로
    var path: String {
        switch self {
        case .healthCheck:
            return "/health"
        case .getAlerts:
            return "/api/v1/alerts"
        case .resolve(let id):
            return "/api/v1/alerts/\(id)/status"
        case .upload:
            return "/api/v1/upload"
        case .createUserFriendlyRule:
            return "/api/v1/rules/user-friendly"
        case .downloadAlertVideo(let id):
            return "/api/v1/alerts/\(id)/video"
        case .getRules:
            return "/api/v1/rules"
        case .deleteRule(let id):          // ✅ [NEW]
            return "/api/v1/rules/\(id)"
        }
    }
    
    // 요청에 필요한 파라미터
    //    var parameters: Parameters? {
    //        switch self {
    //        case .postComment(let text):
    //            return ["text": text]
    //        default:
    //            return nil
    //        }
    //    }
}

// 422 응답 에러 모델
struct APIError: Codable {
    let detail: [APIErrorDetail]
}

struct APIErrorDetail: Codable {
    let loc: [String]
    let msg: String
    let type: String
}
