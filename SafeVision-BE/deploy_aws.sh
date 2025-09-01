#!/bin/bash

# AWS EC2 개발 환경 배포 스크립트
echo "AWS EC2 개발 환경 배포 시작..."

# 기본 VPC 및 네트워크 설정 확인 (간단 버전)
echo "기본 VPC 설정 확인 중..."
echo "현재 VPC 정보:"
aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query 'Vpcs[*].[VpcId,CidrBlock,State]' --output table

echo "기본 서브넷 정보:"
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters 'Name=is-default,Values=true' --query 'Vpcs[0].VpcId' --output text)" --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,State]' --output table

echo "보안 그룹 정보:"
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$(aws ec2 describe-vpcs --filters 'Name=is-default,Values=true' --query 'Vpcs[0].VpcId' --output text)" --query 'SecurityGroups[*].[GroupId,GroupName,Description]' --output table

# 시스템 업데이트
echo "시스템 업데이트 중..."
sudo apt-get update
sudo apt-get upgrade -y

# Python 및 필수 패키지 설치
echo "Python 및 필수 패키지 설치 중..."
sudo apt-get install -y python3 python3-pip python3-venv nginx git

# 프로젝트 디렉토리 생성
echo "프로젝트 디렉토리 생성 중..."
sudo mkdir -p /var/www/smart-safety
sudo chown $USER:$USER /var/www/smart-safety

# 프로젝트 복사 (로컬에서 실행 시)
# scp -r ./* ubuntu@[EC2_IP]:/var/www/smart-safety/

# 가상환경 생성
echo "가상환경 생성 중..."
cd /var/www/smart-safety
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
echo "의존성 설치 중..."
pip install -r requirements.txt

# Nginx 설정
echo "Nginx 설정 중..."
sudo tee /etc/nginx/sites-available/smart-safety << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # SSE 연결을 위한 설정
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
EOF

# Nginx 사이트 활성화
sudo ln -sf /etc/nginx/sites-available/smart-safety /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# systemd 서비스 생성
echo "systemd 서비스 생성 중..."
sudo tee /etc/systemd/system/smart-safety.service << EOF
[Unit]
Description=Smart Safety API
After=network.target

[Service]
Type=exec
User=ubuntu
Group=ubuntu
WorkingDirectory=/var/www/smart-safety
Environment=PATH=/var/www/smart-safety/venv/bin
ExecStart=/var/www/smart-safety/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable smart-safety
sudo systemctl start smart-safety

# 방화벽 설정 (Ubuntu)
echo "🔥 방화벽 설정 중..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "AWS EC2 배포 완료!"
echo "서버 주소: http://[EC2_PUBLIC_IP]"
echo "iOS 앱에서 SSE 연결: http://[EC2_PUBLIC_IP]/api/v1/alerts/sse/alerts"
echo "서비스 상태 확인: sudo systemctl status smart-safety"
echo "로그 확인: sudo journalctl -u smart-safety -f"
