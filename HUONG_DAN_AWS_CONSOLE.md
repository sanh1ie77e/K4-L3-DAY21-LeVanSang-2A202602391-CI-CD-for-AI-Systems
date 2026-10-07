# Thao tác AWS và GitHub cho lab Day 21

Anh làm lần lượt từ mục 1 đến mục 7. Đây là phần AWS của README: S3 lưu dữ liệu/model, EC2 chạy API, GitHub Actions chạy bốn jobs. Các giá trị bên dưới khớp với code đang có trong repo.

Em có thể chạy các lệnh trên máy, kiểm tra DVC, SSH, sửa lỗi và hoàn thiện báo cáo sau khi có tài nguyên. Anh tự đăng nhập, xác nhận MFA, chọn tài khoản thanh toán, tải khóa EC2, nhập GitHub Secrets và nộp bài. Không cần sửa code để làm các mục dưới đây.

## 1. Đăng nhập và chọn region

1. Mở [AWS Console](https://console.aws.amazon.com/), đăng nhập tài khoản của anh, hoàn tất MFA nếu được hỏi.
2. Góc trên bên phải, chọn **Asia Pacific (Sydney)**, mã **ap-southeast-2**. Dùng region này cho cả S3 và EC2. IAM là dịch vụ toàn cục.
3. Bấm tên tài khoản ở góc trên bên phải, ghi lại **Account ID** gồm 12 chữ số, bỏ dấu gạch nối nếu có. Các mục sau dùng ID này.
4. Xem **Billing and Cost Management → Free Tier / Credits** để biết tài khoản còn ưu đãi gì trước khi bấm Launch EC2. EC2, ổ EBS, IPv4 công khai và S3 có thể tính phí; không mặc định lab miễn phí. Tham khảo [EC2](https://aws.amazon.com/ec2/pricing/on-demand/), [EBS](https://aws.amazon.com/ebs/pricing/), [IPv4](https://aws.amazon.com/vpc/pricing/) và [S3](https://aws.amazon.com/s3/pricing/).

Tài khoản thao tác cần quyền tạo S3, IAM role/provider/policy và EC2. Nếu đây là tài khoản do trường/công ty cấp và bị `AccessDenied`, quản trị viên cần cấp quyền hoặc tạo những tài nguyên này cho anh.

## 2. Tạo S3 bucket

S3 là nơi chứa CSV do DVC quản lý và model mà pipeline xuất bản.

1. Ô tìm kiếm trên AWS → gõ **S3** → mở dịch vụ.
2. **General purpose buckets → Create bucket**.
3. Điền:

| Mục trên màn hình | Giá trị |
|---|---|
| AWS Region | Asia Pacific (Sydney), `ap-southeast-2` |
| Bucket type | General purpose |
| Bucket namespace, nếu có | Global |
| Bucket name | Ví dụ `day21-levansang-2a202602391-20261007`; tên phải chưa có người dùng |
| Object Ownership | ACLs disabled / Bucket owner enforced |
| Block Public Access | Giữ **Block all public access** |
| Bucket Versioning | Disable |
| Default encryption | Server-side encryption with Amazon S3 managed keys (**SSE-S3**) |

4. **Create bucket**. Nếu tên trùng, thêm vài chữ số rồi lưu tên mới để dùng nhất quán.

Không upload CSV bằng nút Upload. DVC sẽ tạo `dvc/` khi đẩy dữ liệu; pipeline tạo `artifacts/` sau lần chạy đầu. Bucket giữ private vì EC2 và GitHub đọc bằng IAM role. [Tài liệu tạo bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html).

## 3. Tạo quyền đọc model cho EC2

Role này cho API đọc duy nhất `artifacts/current/model.joblib` trong bucket lab.

1. Tìm **IAM → Policies → Create policy → Visual**.
2. Chọn service **S3**. Tìm và tick đúng action **GetObject**.
3. Trong **Resources**, chọn **Specific**. Ở loại **object**, bấm **Add ARNs**.
4. Nhập bucket name ở mục 2 và object name `artifacts/current/model.joblib`. ARN cuối cùng phải là:

   ```text
   arn:aws:s3:::TEN_BUCKET_CUA_ANH/artifacts/current/model.joblib
   ```

5. **Next**, đặt tên policy **income-lab-ec2-read-model**, **Create policy**.
6. **IAM → Roles → Create role → AWS service → EC2** (use case EC2) → **Next**.
7. Tìm và tick policy **income-lab-ec2-read-model** → **Next**.
8. Đặt tên role **income-lab-ec2** → **Create role**.

Console tạo instance profile đi kèm role EC2. Ở bước tạo máy, chọn profile này để SDK tự nhận credentials. [Tạo service role](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-service.html).

## 4. Tạo quyền AWS cho GitHub Actions

GitHub dùng OIDC để nhận credentials tạm thời. Workflow hiện tại đọc `STORAGE_CREDENTIALS` dưới dạng role ARN + region; anh không cần tạo access key để bỏ vào GitHub.

### 4.1. Thêm identity provider

1. **IAM → Identity providers → Add provider**.
2. Chọn **OpenID Connect**.
3. **Provider URL**: `https://token.actions.githubusercontent.com`.
4. **Audience**: `sts.amazonaws.com`.
5. **Add provider**. Nếu provider này đã tồn tại, dùng lại và kiểm tra audience.

[Tài liệu OIDC của GitHub trên AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).

### 4.2. Tạo policy cho pipeline

**IAM → Policies → Create policy → Visual**. Tạo các khối quyền S3 bằng **Add more permissions**. Chọn **Specific** cho Resources; không tick toàn bộ quyền S3.

| Khối | Actions cần tick | Resource cần thêm bằng Add ARNs |
|---|---|---|
| 1 | `GetBucketLocation`, `ListBucket` | bucket: `arn:aws:s3:::TEN_BUCKET_CUA_ANH` |
| 2 | `GetObject` | object: `arn:aws:s3:::TEN_BUCKET_CUA_ANH/dvc/*` |
| 3 | `GetObject`, `PutObject` | object: `arn:aws:s3:::TEN_BUCKET_CUA_ANH/artifacts/*` |

Trong popup Add ARNs, với khối 1 điền bucket name; khối 2 điền bucket name và object name `dvc/*`; khối 3 điền bucket name và object name `artifacts/*`. Dấu `*` ở cuối là có chủ ý để bao gồm các file trong prefix.

**Next → Policy name: income-lab-github-storage → Create policy**.

Model đọc/copy/upload sử dụng quyền S3 đã được phân tích bằng IAM Policy Autopilot; `deploy/iam-runtime-baseline.json` giữ bản phân tích để đối chiếu. Các bước Visual trên giới hạn quyền theo cấu hình SSE-S3, ACL disabled của lab và bổ sung quyền đọc remote DVC. Bản baseline chưa giới hạn tài nguyên, không dùng nguyên bản để gắn lên role. `HeadObject` dùng `GetObject`; copy model cần đọc nguồn và ghi đích. [Quyền cho API S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html).

Lệnh tái tạo phân tích nếu cần, không tạo hoặc gắn policy trên AWS:

```powershell
$taskRepoRoot = (Get-Location).Path
uvx iam-policy-autopilot@latest generate-policies (Join-Path $taskRepoRoot 'src/serve.py') (Join-Path $taskRepoRoot 'src/artifacts.py') --service-hints s3 --pretty
```

### 4.3. Tạo role GitHub với trust policy đúng repo

1. **IAM → Roles → Create role → Custom trust policy**.
2. Dán JSON bên dưới, thay **ACCOUNT_ID_CUA_ANH** bằng Account ID ở mục 1. Không thay hai ID GitHub: em đã đọc metadata thật của repo này, được tạo ngày 07/10/2026.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID_CUA_ANH:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:sanh1ie77e@142182062/K4-L3-DAY21-LeVanSang-2A202602391-CI-CD-for-AI-Systems@1408188457:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

3. **Next** → tick policy **income-lab-github-storage** → **Next**.
4. Role name **income-lab-github** → **Create role**.
5. Mở role vừa tạo, copy **ARN** dạng `arn:aws:iam::123456789012:role/income-lab-github`, lưu để nhập Secret.

Repo mới dùng subject chứa owner ID và repository ID theo [quy tắc OIDC của GitHub](https://docs.github.com/en/actions/reference/security/oidc#immutable-subject-claims). Trust policy này chỉ chấp nhận branch `main` của repo hiện tại. Nếu đổi tên/chuyển repo, cần cập nhật tên trong subject.

## 5. Tạo EC2 chạy API

1. Tìm **EC2**, kiểm tra góc trên là **Sydney**, chọn **Instances → Launch instances**.
2. Điền các mục sau:

| Mục | Giá trị cho lab |
|---|---|
| Name | `income-lab-api` |
| Application and OS Images | Ubuntu Server **22.04 LTS**, publisher Canonical, **64-bit (x86)** |
| Instance type | `t3.micro` cho API nhỏ này; xem giá/ưu đãi của tài khoản trong Summary |
| Key pair | Create new key pair → name `income_deploy`, type RSA, format `.pem` |
| Network settings → VPC / subnet | Default VPC và default subnet có kết nối Internet |
| Auto-assign public IP | Enable |
| Security group | Create security group, name `income-lab-sg` |
| Configure storage | Root volume 8 GiB, `gp3`; bật Encrypted trong phần Advanced |
| Advanced details → IAM instance profile | `income-lab-ec2` |
| Advanced details → Metadata accessible | Enabled |
| Advanced details → Metadata version | V2 only / token required |
| Advanced details → Credit specification | Standard nếu có lựa chọn; không chọn Unlimited cho lab này |

3. Khi tạo key pair, trình duyệt tải **income_deploy.pem**. Chuyển file vào thư mục `deploy/` trong repo; file `.pem` đã được Git bỏ qua. Giữ file trên máy, không gửi nội dung khóa qua chat hoặc commit Git.
4. **Network settings → Edit → Add security group rule**; cần hai inbound rules:

| Type | Port | Source |
|---|---|---|
| SSH | 22 | Anywhere-IPv4 (`0.0.0.0/0`) tạm trong hai lần chạy lab |
| Custom TCP | 8080 | Anywhere-IPv4 (`0.0.0.0/0`) cho API của đề |

Workflow hiện dùng GitHub hosted runner SSH vào EC2; IP runner thay đổi, nên chỉ chọn My IP cho SSH sẽ chặn bước Release. Rule SSH Anywhere cho phép kết nối từ Internet; dùng khóa của lab và đổi về **My IP** sau khi chạy/chụp xong hai pipeline. Khi SSH chỉ còn My IP, lần triển khai tiếp theo từ GitHub sẽ cần điều chỉnh rule lại. [Hướng dẫn mạng và SSH của EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html).

5. Kiểm tra **Summary** rồi **Launch instance**. Đợi **Running** và các **Status checks passed**.
6. Mở instance → **Details** → copy **Public IPv4 address**. Đây là `SERVER_HOST`, không dùng Private IPv4.
7. Tab **Security → IAM role** phải là `income-lab-ec2`. Nếu quên gắn: **Actions → Security → Modify IAM role → income-lab-ec2 → Update IAM role**.

Nếu AWS không có Default VPC/subnet, dừng ở phần Network settings để em hướng dẫn mạng theo màn hình thực tế. Nếu chỉ thấy Ubuntu 24.04, đổi bộ lọc/tìm AMI Ubuntu 22.04 của Canonical; môi trường phục vụ đang dùng Python 3.10 của Ubuntu 22.04.

IMDS phải bật để EC2 lấy credentials từ role; chọn [IMDSv2 required](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html). T3 có thể mặc định Unlimited; chế độ Standard tránh phụ phí surplus CPU credits, nhưng CPU sẽ bị giới hạn khi hết credits. [Cấu hình CPU credits](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances-how-to.html).

### Chuẩn bị máy một lần

Phần lệnh này em chạy được sau khi có tên bucket, IP và file `.pem`. Nếu anh muốn tự chạy, mở PowerShell tại thư mục gốc repo. Thay hai giá trị đầu bằng tài nguyên vừa tạo; chạy từng khối và dừng nếu có lỗi.

```powershell
$env:ARTIFACT_BUCKET = 'TEN_BUCKET_CUA_ANH'
$env:SERVER_HOST = 'PUBLIC_IPV4_EC2'
$env:AWS_DEFAULT_REGION = 'ap-southeast-2'
$taskVmTarget = 'ubuntu@' + $env:SERVER_HOST
scp -i .\deploy\income_deploy.pem .\deploy\bootstrap-ec2.sh ($taskVmTarget + ':~/bootstrap-ec2.sh')
if ($LASTEXITCODE -ne 0) { throw 'SCP thất bại; dừng lại' }
```

Lần kết nối đầu, đối chiếu host fingerprint qua **EC2 → Connect → SSH client** hoặc lấy fingerprint theo [hướng dẫn AWS](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connection-prereqs.html), rồi xác nhận `yes` nếu đúng.

```powershell
ssh -i .\deploy\income_deploy.pem $taskVmTarget "sudo bash ~/bootstrap-ec2.sh $env:ARTIFACT_BUCKET $env:AWS_DEFAULT_REGION ubuntu"
if ($LASTEXITCODE -ne 0) { throw 'Bootstrap EC2 thất bại; dừng lại' }
```

Khi hiện `EC2 prepared...`, máy đã sẵn sàng. Service chưa chạy ở thời điểm này; pipeline xuất bản model, copy code rồi mới khởi động API. Không cần cài AWS access key hoặc đăng nhập AWS CLI trên EC2.

## 6. Thêm đúng năm GitHub Secrets

Mở [repository của anh](https://github.com/sanh1ie77e/K4-L3-DAY21-LeVanSang-2A202602391-CI-CD-for-AI-Systems) → **Settings → Secrets and variables → Actions → New repository secret**. Tạo từng secret rồi bấm **Add secret**:

| Name | Secret |
|---|---|
| `ARTIFACT_BUCKET` | Tên bucket thật, không có `s3://` và không có `/dvc` |
| `SERVER_HOST` | Public IPv4 của EC2, không có `http://`, `:8080` hay `ubuntu@` |
| `SERVER_USER` | `ubuntu` |
| `SERVER_SSH_KEY` | Mở `deploy/income_deploy.pem` bằng editor, copy toàn bộ nội dung gồm dòng BEGIN và END |
| `STORAGE_CREDENTIALS` | JSON bên dưới, thay ARN bằng ARN role **income-lab-github** thật |

```json
{"role_arn":"arn:aws:iam::ACCOUNT_ID_CUA_ANH:role/income-lab-github","region":"ap-southeast-2"}
```

Không dùng ARN role EC2 cho `STORAGE_CREDENTIALS`. Đăng nhập AWS trên laptop không thay thế role của GitHub. [GitHub repository secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

## 7. Đăng nhập CLI, đẩy DVC rồi chạy pipeline

Đây là các lệnh em có thể chạy; cửa sổ đăng nhập và MFA vẫn do anh xác nhận. Nếu tự chạy, dùng PowerShell ở thư mục gốc repo. Không cần cài lại Python; `.venv` Python 3.10 đã có.

```powershell
. .\.venv\Scripts\Activate.ps1
aws login --profile day21-console --region ap-southeast-2
aws sts get-caller-identity --profile day21-console
```

Trong trình duyệt mở ra, chọn đúng tài khoản đã tạo bucket và EC2 rồi xác nhận. Nếu IAM báo thiếu quyền đăng nhập local: **IAM → Users → user của anh → Add permissions → Attach policies directly → SignInLocalDevelopmentAccess**; nếu đang dùng role, gắn policy này lên role. Quản trị viên làm bước đó nếu anh không có quyền IAM. [AWS CLI login](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html).

Bản DVC của lab dùng SDK cũ, nên dùng profile process để SDK lấy credentials tạm thời từ CLI:

```powershell
aws configure set credential_process 'aws configure export-credentials --profile day21-console --format process' --profile day21
aws configure set region ap-southeast-2 --profile day21
$env:AWS_PROFILE = 'day21'
$env:AWS_DEFAULT_REGION = 'ap-southeast-2'
$env:ARTIFACT_BUCKET = 'TEN_BUCKET_CUA_ANH'
aws sts get-caller-identity
```

Account trả về phải khớp mục 1. Danh tính đăng nhập cũng cần quyền ghi dữ liệu trong prefix `dvc/`; policy GitHub ở mục 4 chỉ đọc DVC. Nếu tài khoản IAM bị từ chối khi `dvc push`, em sẽ kiểm tra lỗi cụ thể và hướng dẫn quyền cho danh tính local.

Repo này đã `dvc init` và `dvc add` ba CSV. Chỉ cần:

```powershell
dvc remote add --force -d labstore "s3://$env:ARTIFACT_BUCKET/dvc"
dvc push
if ($LASTEXITCODE -ne 0) { throw 'DVC push lỗi; chưa git push' }
```

Vào **S3 → bucket → Objects → Refresh**, phải thấy `dvc/` có dữ liệu. Sau đó mới commit/push code, workflow và các con trỏ `.dvc`:

```powershell
git status --short
git add .
git diff --cached --name-only
```

Danh sách commit không được chứa `.pem`, credentials, `.env` hay file trong `.aws/`. Các file code/cấu hình lab và hướng dẫn được commit bình thường.

```powershell
git commit -m 'feat: triển khai lab Day21 với S3 EC2 và GitHub OIDC'
git push origin main
if ($LASTEXITCODE -ne 0) { throw 'Git push lỗi; dừng để kiểm tra' }
```

Mở GitHub → **Actions → Income Model CI/CD**. Chờ **Unit Test → Train → Quality Gate → Release** xanh. Nếu code đã push nhưng chưa có run: **Run workflow → Branch main → Run workflow**. [Chạy workflow thủ công](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

Kiểm tra bằng PowerShell với IP EC2 thật:

```powershell
$env:SERVER_HOST = 'PUBLIC_IPV4_EC2'
Invoke-RestMethod "http://$($env:SERVER_HOST):8080/healthz"
Invoke-RestMethod -Method Post -Uri "http://$($env:SERVER_HOST):8080/score" -ContentType 'application/json' -Body '{"features":[28,2,14,2,11,0,1,0,0,45]}' | ConvertTo-Json
```

Kết quả cần có `status: ok` và dự đoán hợp lệ. S3 phải có `artifacts/current/model.joblib`, `report.json`, `detail.txt`.

## 8. Những việc còn lại ngoài code để nộp bài

1. **Chụp màn hình thật**, lưu vào `nop-bai/anh-chup-man-hinh/`:

   | Tên ảnh | Màn hình cần chụp |
   |---|---|
   | `01-mlflow-ui.png` | MLflow local, ít nhất 3 runs, F1 + accuracy + 3 tham số |
   | `02-actions-buoc-2.png` | Lần chạy trên batch 1, bốn jobs xanh |
   | `03-actions-buoc-3.png` | Lần chạy tự kích hoạt bởi commit ghép batch 2, bốn jobs xanh |
   | `04-curl-api.png` | Terminal hiện địa chỉ EC2 thật và cả kết quả healthz + score |
   | `05-cloud-storage.png` | S3 bucket có `dvc/` và `artifacts/current/model.joblib` |

   Với ảnh 04, đề dùng `curl`; anh có thể chụp lệnh `Invoke-RestMethod` bên trên để thấy hai kết quả. Nếu muốn đúng cú pháp curl trên Windows, dùng `curl.exe` với payload trong file như hướng dẫn dưới đây. Ảnh S3 có thể tách thành `05a-storage-dvc.png` và `05b-storage-model.png` theo checklist. Ảnh trình duyệt cần thấy URL; không chụp nội dung khóa hoặc Secrets. Xem yêu cầu gốc trong [checklist ảnh](nop-bai/anh-chup-man-hinh/README.md).

   ```powershell
   '{"features":[28,2,14,2,11,0,1,0,0,45]}' | Set-Content -Encoding ascii .\outputs\score-request.json
   curl.exe "http://$($env:SERVER_HOST):8080/healthz"
   curl.exe -X POST "http://$($env:SERVER_HOST):8080/score" -H 'Content-Type: application/json' --data-binary '@outputs/score-request.json'
   ```

2. **Bước 3 chỉ làm sau khi Bước 2 xanh**. Em chạy được phần ghép batch, DVC và Git khi anh muốn tiếp tục. Nếu tự chạy:

   ```powershell
   python append_batch.py
   if ($LASTEXITCODE -ne 0) { throw 'Ghép batch lỗi; dừng lại' }
   dvc add data/train_batch1.csv
   dvc push
   if ($LASTEXITCODE -ne 0) { throw 'DVC push lỗi; chưa git push' }
   git add data/train_batch1.csv.dvc
   git commit -m 'data: bổ sung 22361 mẫu dữ liệu mới (train_batch2)'
   git push origin main
   ```

   Đợi lần chạy do commit dữ liệu này kích hoạt, chụp ảnh 03. Không bấm Run workflow thay cho bằng chứng tự động ở Bước 3.

3. **Lấy số liệu thật từ Actions**: mỗi run → job **Train** có số mẫu/F1/accuracy trong Summary; artifact **report** chứa `report.json` và `detail.txt`. Em dùng hai báo cáo thật để điền so sánh Bước 2/Bước 3 trong `nop-bai/bao-cao.md`. Chưa dùng số mô phỏng local như bằng chứng cloud.
4. **Nộp bài**: commit/push thư mục `nop-bai/`, kiểm tra repo public bằng cửa sổ ẩn danh rồi dán [URL repo](https://github.com/sanh1ie77e/K4-L3-DAY21-LeVanSang-2A202602391-CI-CD-for-AI-Systems) vào bài nộp trên [vlearn.dev](https://vlearn.dev). Anh tự đăng nhập và bấm nộp.
5. **Sau khi không cần máy cho chấm bài**: EC2 → Instances → instance lab → **Instance state → Terminate instance**; kiểm tra ổ EBS còn lại. Nếu vẫn cần giữ máy, Stop để ngừng compute, nhưng EBS vẫn tính phí; khi Start lại, public IP có thể đổi và phải cập nhật `SERVER_HOST`. S3 tiếp tục tính lưu trữ cho đến khi xóa dữ liệu. Chỉ xóa bucket/roles của lab khi đã nộp và không cần chúng nữa; lưu model/báo cáo cần giữ trước khi xóa.

## 9. Khi lỗi, xem đúng nơi

| Lỗi | Kiểm tra |
|---|---|
| GitHub không assume được role | `STORAGE_CREDENTIALS` dùng ARN role GitHub; trust policy có đúng hai ID trong mục 4; provider/audience đúng |
| Train không pull được DVC | DVC đã push thành công trước Git; role GitHub có ListBucket/GetObject; tên bucket đúng |
| Release SSH timeout | EC2 Running, dùng Public IPv4; inbound TCP 22 cho runner |
| SSH Permission denied (publickey) | User `ubuntu`; `.pem` đúng key pair lúc tạo EC2; Secret chứa cả BEGIN/END |
| Windows báo private key permissions quá rộng | Cần chỉnh ACL file `.pem` trên máy; gửi em dòng lỗi để em xử lý quyền file |
| API lỗi đọc S3 / NoCredentials | EC2 đã gắn `income-lab-ec2`; IMDS Enabled; policy đọc đúng tên bucket/model |
| API 8080 không truy cập được | Inbound TCP 8080; dùng public IP mới nhất; xem log service |
| Quality Gate đỏ, Release skipped | Đúng cơ chế khi F1 dưới 0,65; xem report của lần chạy trước khi đổi cấu hình |

Lệnh đọc log máy chủ, em có thể chạy hoặc anh chạy sau khi SSH:

```bash
sudo systemctl status income-api --no-pager
sudo journalctl -u income-api -n 80 --no-pager
```

Để em nối tiếp phần lệnh, anh chỉ cần cho biết **tên bucket, public IP EC2, ARN role GitHub và vị trí file `.pem` trên máy**. Không gửi nội dung khóa, password hoặc mã MFA.
