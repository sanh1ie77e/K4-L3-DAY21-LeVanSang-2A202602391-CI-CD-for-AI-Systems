# Lab Day 21 trên Windows và AWS

Repository này dùng nhánh AWS của README: S3 thay GCS, EC2 thay GCE, `dvc[s3]` và `boto3` thay các thư viện GCP. Ba bước của đề, dữ liệu, thứ tự đặc trưng và ngưỡng F1 giữ nguyên. Các file `tasks/` giữ ví dụ gốc để đối chiếu.

Chạy các lệnh từ thư mục gốc repository, lần lượt từng khối và dừng nếu có lỗi. Môi trường `.venv` hiện dùng Python 3.10.16. Bộ thư viện này phù hợp với Python 3.10–3.12.

## Chuẩn bị môi trường theo README

Git, AWS CLI và remote GitHub đã có; không cần clone lại.

```powershell
. .\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements.txt
python -m pip check
git --version
aws --version
```

Nếu cần tạo môi trường mới, dùng Python 3.10 đã có trong repo:

```powershell
& '.\.python\cpython-3.10.16-windows-x86_64-none\python.exe' -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Trong VS Code, chọn **Python: Select Interpreter → .venv/Scripts/python.exe**. Có thể gọi trực tiếp executable này khi không kích hoạt môi trường.

```powershell
$env:MLFLOW_TRACKING_URI = 'sqlite:///mlflow.db'
$env:MLFLOW_ARTIFACT_ROOT = './mlartifacts'
$env:MLFLOW_EXPERIMENT_NAME = 'Adult-Income'
```

Các biến có hiệu lực trong terminal hiện tại. `.env.example` chỉ là mẫu; chương trình không tự nạp `.env`.

## Bước 1: dữ liệu và ba thí nghiệm MLflow

Chỉ tải dữ liệu nếu chưa có ba CSV. Chạy lại sau Bước 3 sẽ đặt lại batch huấn luyện.

```powershell
python prepare_data.py
python -m pytest tests/ -q
python run_experiments.py
python src/quality_gate.py outputs/report.json
mlflow ui --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Kích thước theo đề: hai batch mỗi file 22.361 mẫu, holdout 500 mẫu. Script dùng bản ZIP chính thức từ UCI; hỗ trợ `--raw-dir` nếu đã có `adult.data` và `adult.test`.

Mở http://localhost:5000, chọn **Adult-Income**, lọc tag `stage = step1`, hiện cột F1, accuracy và ba siêu tham số. Script chạy đúng ba cấu hình của đề, chọn F1 cao nhất, ghi `params.yaml`, giữ model và báo cáo tương ứng. Kết quả ở `outputs/experiments.json`; precision, recall và confusion matrix ở `outputs/detail.txt`. Chụp UI thật thành `nop-bai/anh-chup-man-hinh/01-mlflow-ui.png`.

Thử API trong terminal khác:

```powershell
. .\.venv\Scripts\Activate.ps1
Remove-Item Env:ARTIFACT_BUCKET -ErrorAction SilentlyContinue
$env:MODEL_PATH = (Join-Path (Get-Location) 'models/model.joblib')
python src/serve.py
```

Trong terminal thứ ba:

```powershell
Invoke-RestMethod http://localhost:8080/healthz
Invoke-RestMethod -Method Post -Uri http://localhost:8080/score -ContentType 'application/json' -Body '{"features":[28,2,14,2,11,0,1,0,0,45]}'
```

API giữ đúng 10 đặc trưng theo README và trả `prediction`, `label`.

## Bước 2: AWS, DVC và CI/CD

Cloud cần phiên AWS CLI đã đăng nhập và có quyền tạo hạ tầng. Trợ lý chạy `aws login` sau khi anh xác nhận; trình duyệt mở để anh đăng nhập tài khoản AWS. Kiểm tra bằng `aws sts get-caller-identity`.

Nếu SDK hoặc DVC chưa đọc được phiên đăng nhập, AWS hỗ trợ profile process dùng credentials tạm thời từ CLI:

```powershell
# Sau khi profile default đã đăng nhập thành công:
aws configure set credential_process 'aws configure export-credentials --profile default --format process' --profile day21
aws configure set region ap-southeast-2 --profile day21
$env:AWS_PROFILE = 'day21'
$env:AWS_DEFAULT_REGION = 'ap-southeast-2'
aws sts get-caller-identity
```

Dùng cùng region với tài nguyên thực tế. `ap-southeast-2` là mặc định của hướng dẫn. Profile cục bộ không được sao chép vào EC2 hoặc CI. [Tài liệu đăng nhập AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html).

### S3 và DVC

Sau khi chọn tên bucket thật, duy nhất:

```powershell
$env:ARTIFACT_BUCKET = 'TEN_BUCKET_THAT_CUA_ANH'
aws s3 mb "s3://$env:ARTIFACT_BUCKET" --region $env:AWS_DEFAULT_REGION
```

Bucket dùng Block Public Access, Bucket owner enforced và mã hóa SSE-S3. [Hướng dẫn bảo vệ S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html). S3 tính phí lưu trữ, requests và một số loại truyền dữ liệu; xem [giá S3](https://aws.amazon.com/s3/pricing/). Versioning giữ các phiên bản cũ và tăng lượng lưu trữ, nên không tự bật cho lab.

```text
dvc/                               # dữ liệu DVC
artifacts/runs/<run-id>-<attempt>/  # ứng viên mỗi lần chạy
artifacts/current/model.joblib     # model đã qua quality gate
artifacts/current/report.json
artifacts/current/detail.txt
```

```powershell
# Bỏ qua dvc init nếu đã có .dvc/.
dvc init
dvc remote add --force -d labstore "s3://$env:ARTIFACT_BUCKET/dvc"
dvc add data/train_batch1.csv data/holdout.csv data/train_batch2.csv
dvc push
if ($LASTEXITCODE -ne 0) { throw 'DVC push thất bại; dừng trước git push' }
git add .dvc/config data/*.dvc .gitignore
```

DVC đọc credentials từ profile AWS hoặc biến môi trường. Nhánh AWS không dùng service-account JSON hoặc `credentialpath` của GCP.

### EC2

Dùng Ubuntu 22.04 x86-64, cùng region với S3, EBS gp3 mã hóa và IMDSv2 bắt buộc. Gắn instance profile cho API đọc đúng model của lab từ S3; không copy access key lên VM. Security Group cần kết nối API TCP 8080 theo đề và SSH cho người quản trị, runner triển khai. Cấu hình SSH khi đã biết IP và Security Group thực tế; chỉ mở cho IP máy cá nhân chưa đủ cho GitHub hosted runner.

EC2, EBS và IPv4 công khai có thể phát sinh phí tùy region, loại instance và thời gian chạy. Kiểm tra điều kiện Free Tier của tài khoản, không mặc định miễn phí. [Giá EC2](https://aws.amazon.com/ec2/pricing/on-demand/), [giá EBS](https://aws.amazon.com/ebs/pricing/).

Sau khi có EC2, khóa SSH và tên bucket thật:

```powershell
$taskVmTarget = 'ubuntu@' + $env:SERVER_HOST
scp -i deploy/income_deploy.pem deploy/bootstrap-ec2.sh ($taskVmTarget + ':~/bootstrap-ec2.sh')
ssh -i deploy/income_deploy.pem $taskVmTarget "sudo bash ~/bootstrap-ec2.sh $env:ARTIFACT_BUCKET $env:AWS_DEFAULT_REGION ubuntu"
```

Script chuẩn bị môi trường, thư mục và service `income-api`, cấp quyền restart service cho user triển khai. Service chưa chạy trước khi pipeline xuất bản model lần đầu. Private key tương ứng public key trên EC2 và phải nằm ngoài Git.

### IAM và năm GitHub Secrets

EC2 dùng instance profile. GitHub Actions dùng OIDC để nhận credentials tạm thời theo [hướng dẫn action AWS](https://github.com/aws-actions/configure-aws-credentials). Role chỉ tin cậy repo này trên branch `main`, audience `sts.amazonaws.com`. Dùng subject thực tế của repo: GitHub có thể thêm owner ID và repository ID vào `sub`; không đoán ID. [OIDC subject của GitHub](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims).

Có thể tái tạo bản phân tích quyền SDK:

```powershell
$taskRepoRoot = (Get-Location).Path
uvx iam-policy-autopilot@latest generate-policies (Join-Path $taskRepoRoot 'src/serve.py') (Join-Path $taskRepoRoot 'src/artifacts.py') --service-hints s3 --pretty
```

`deploy/iam-runtime-baseline.json` là kết quả phân tích, chưa phải policy để gắn lên role. Kết quả có các quyền rộng cho biến thể API, cần rà soát và giới hạn trên bucket lab trước khi áp dụng. CI cũng cần quyền đọc/liệt kê prefix `dvc/`. Chưa có role nào được tạo hoặc gắn policy bởi phân tích cục bộ.

Vẫn dùng đúng năm tên secret của README:

| Secret | Giá trị bản AWS |
|---|---|
| `STORAGE_CREDENTIALS` | JSON chứa `role_arn` của role OIDC và `region` |
| `ARTIFACT_BUCKET` | Tên S3 bucket, không có `s3://` |
| `SERVER_HOST` | IP/DNS công khai của EC2 |
| `SERVER_USER` | `ubuntu` với AMI Ubuntu |
| `SERVER_SSH_KEY` | Nội dung private key SSH tương ứng public key trên EC2 |

Ví dụ cấu trúc, thay bằng account/role thật:

```json
{"role_arn":"arn:aws:iam::<ACCOUNT_ID>:role/income-lab-github","region":"ap-southeast-2"}
```

JSON mô tả role, không chứa access key. `aws-actions/configure-aws-credentials` dùng OIDC trên runner. Đăng nhập AWS cục bộ không tự đăng nhập runner.

Pipeline giữ **Unit Test → Train → Quality Gate → Release**. Train pull dữ liệu S3 bằng DVC, đưa ứng viên vào `artifacts/runs/`. Gate chặn F1 dưới 0,65. Release kiểm tra lại báo cáo, cập nhật `artifacts/current/`, copy code lên EC2, cài đúng thư viện, restart service, kiểm tra cả hai endpoint.

Chỉ push Git sau khi `dvc push` thành công. Theo dõi Actions, gọi API qua IP EC2 và chụp ảnh thật 02, 04, 05 theo checklist.

## Bước 3: bổ sung dữ liệu và kích hoạt pipeline

Làm sau khi Bước 2 đã chạy xanh trên AWS:

```powershell
python append_batch.py
(Get-Content data/train_batch1.csv | Measure-Object -Line).Lines # 44723
dvc add data/train_batch1.csv
dvc push
if ($LASTEXITCODE -ne 0) { throw 'DVC push thất bại; dừng trước git push' }
git add data/train_batch1.csv.dvc
git commit -m 'data: bổ sung 22361 mẫu dữ liệu mới (train_batch2)'
git push origin main
```

Script từ chối ghép batch lần thứ hai. Commit con trỏ DVC kích hoạt lại pipeline. So sánh hai báo cáo Actions và lưu ảnh 03.

Có thể chạy `python compare_batches.py` trước để so sánh cục bộ: kết quả ở `outputs/batch-comparison.json`, giữ nguyên batch gốc và model đang chọn. Mô phỏng này chưa chứng minh CI/CD hoặc triển khai AWS.

## Nộp bài

Hoàn thiện `nop-bai/bao-cao.md`, đủ năm ảnh thật, kiểm tra `nop-bai/README.md`, rồi nộp URL repo public. Chỉ điền kết quả AWS và đánh dấu hoàn thành khi pipeline, S3, EC2 đã được kiểm chứng thực tế.
