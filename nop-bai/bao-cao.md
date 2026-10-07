# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

| | |
|---|---|
| Họ và tên | Lê Văn Sang |
| MSSV | 2A202602391 |
| Lớp / Khóa | K4 |
| Repo GitHub | https://github.com/sanh1ie77e/K4-L3-DAY21-LeVanSang-2A202602391-CI-CD-for-AI-Systems |
| Ngày nộp | Chưa nộp; cần hoàn thành kiểm chứng AWS |

---

## 1. Bộ Siêu Tham Số Đã Chọn và Lý Do

Kết quả thực nghiệm cục bộ trên 22.361 mẫu huấn luyện và 500 mẫu holdout cố định:

| Lần chạy | n_estimators | learning_rate | max_depth | f1_score | accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.710900 | 0.878000 |
| 2 | 50 | 0.05 | 2 | 0.605128 | 0.846000 |
| 3 | 200 | 0.1 | 5 | 0.714932 | 0.874000 |

**Bộ siêu tham số đã chọn:** `n_estimators=200`, `learning_rate=0.1`, `max_depth=5`.

**Lý do:** Lần 3 có F1 cao nhất và vượt ngưỡng 0,65. Lần 1 có accuracy cao nhất nhưng F1 thấp hơn, nên không được chọn. Cấu hình 50 cây với learning rate 0,05 và độ sâu 2 chưa đạt ngưỡng. Do ba cấu hình thay đổi nhiều tham số cùng lúc, chưa thể kết luận tác động riêng của từng tham số.

---

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Lớp thu nhập cao chiếm khoảng 24,8%. Mô hình luôn dự đoán thu nhập thấp vẫn có accuracy khoảng 75,2% nhưng F1 lớp dương bằng 0. F1 kết hợp precision và recall để đánh giá khả năng nhận diện lớp thu nhập cao. Vì vậy quality gate kiểm tra F1 của target=1, không dùng accuracy, macro hoặc weighted F1. Accuracy vẫn được ghi vào MLflow để tham khảo.

---

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| Cài scikit-learn thất bại | Python 3.13 không phù hợp với bộ thư viện ghim | Dùng Python 3.10.16 và môi trường .venv |
| Cấu hình cloud chưa đúng tài khoản hiện có | Đề lấy GCP làm ví dụ, người thực hiện dùng AWS | Chuyển DVC sang S3, SDK sang boto3 và API chạy trên EC2 |
| SSH từ Windows từ chối khóa riêng | Quyền truy cập file PEM quá rộng | Giới hạn quyền file cho tài khoản sở hữu; kết nối SSH và chạy bootstrap EC2 thành công |

**Trạng thái kiểm chứng ngày 07/10/2026:** Đã đăng nhập AWS CLI và đẩy 3 file dữ liệu DVC lên S3. GitHub chưa có lần chạy Actions; S3 chưa có `artifacts/current/model.joblib`; chưa kết nối được API EC2 cổng 8080. Cần hoàn thành hai lần chạy CI/CD và lưu ảnh bằng chứng trước khi nộp.

---

## 4. So Sánh Bước 2 và Bước 3 (bắt buộc, 2 - 3 câu)

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (chỉ `train_batch1`) | Chưa có artifact Actions | Chưa có artifact Actions |
| Bước 3 (thêm `train_batch2`) | Chưa có artifact Actions | Chưa có artifact Actions |

**Nhận xét:** Mô phỏng cục bộ cho F1 tăng từ 0,714932 lên 0,735426 và accuracy tăng từ 0,874 lên 0,882 khi ghép thêm dữ liệu, giữ nguyên holdout. Các số này chưa phải kết quả CI/CD trên AWS; cần thay bảng bằng artifact của hai lần chạy Actions thực tế trước khi nộp.
