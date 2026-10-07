# Báo cáo Day 21 - CI/CD cho AI Systems

**Lê Văn Sang - MSSV 2A202602391 - K4**

Ngày lập: 07/10/2026. [Repo GitHub](https://github.com/sanh1ie77e/K4-L3-DAY21-LeVanSang-2A202602391-CI-CD-for-AI-Systems).

## 1. Siêu tham số và lựa chọn

Ba thí nghiệm MLflow dùng 22.361 mẫu train và 500 mẫu holdout:

| Run | n_estimators | learning_rate | max_depth | F1 | Accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.710900 | 0.878 |
| 2 | 50 | 0.05 | 2 | 0.605128 | 0.846 |
| 3 | 200 | 0.1 | 5 | 0.714932 | 0.874 |

Chọn **200 cây, learning_rate=0.1, max_depth=5** vì F1 cao nhất và vượt 0.65. Run 1 có accuracy cao hơn nhưng F1 thấp hơn. Ba cấu hình thay đổi nhiều tham số nên chưa tách được tác động riêng từng tham số.

## 2. Vì sao dùng F1 thay accuracy

Lớp thu nhập cao chỉ chiếm khoảng 24.8%. Luôn dự đoán thu nhập thấp vẫn cho accuracy khoảng 75.2% nhưng F1 lớp dương bằng 0. F1 kết hợp precision và recall; gate dùng F1 của target=1, accuracy được ghi để tham khảo.

## 3. Khó khăn và kiểm chứng triển khai

Python 3.13 không phù hợp thư viện ghim: chuyển sang Python 3.10.16. Triển khai bằng AWS S3/EC2 thay ví dụ GCP. SSH Windows từ chối PEM do quyền quá rộng: giới hạn quyền cho chủ sở hữu. Release lỗi khóa/IP: cập nhật Secrets bằng toàn bộ PEM, IP EC2 và user ubuntu.

Đã lưu dữ liệu DVC trên S3 và model tại artifacts/current/model.joblib. API EC2 trả status=ok và nhãn hợp lệ. [Gate thử nghiệm](https://github.com/sanh1ie77e/K4-L3-DAY21-LeVanSang-2A202602391-CI-CD-for-AI-Systems/actions/runs/37583426297/attempts/1), commit 93c5684: F1=0.605128 khiến Quality Gate thất bại, Release skipped; sau đó khôi phục cấu hình tốt.

## 4. So sánh CI/CD thực tế Bước 2 và Bước 3

| Lần chạy | Mẫu train | F1 | Accuracy |
|---|---|---|---|
| [Bước 2, #3](https://github.com/sanh1ie77e/K4-L3-DAY21-LeVanSang-2A202602391-CI-CD-for-AI-Systems/actions/runs/37583784857) | 22.361 | 0.714932 | 0.874 |
| [Bước 3, #4](https://github.com/sanh1ie77e/K4-L3-DAY21-LeVanSang-2A202602391-CI-CD-for-AI-Systems/actions/runs/37584491283) | 44.722 | 0.735426 | 0.882 |

Thêm batch2 làm F1 tăng 0.020494 và accuracy tăng 0.008, giữ nguyên tham số và 500 mẫu holdout. Hai batch cùng phân phối; tăng số mẫu có thể giúp mô hình học thêm trường hợp, nhưng mức cải thiện trên holdout này chưa đủ kết luận thêm dữ liệu luôn tốt hơn. Commit cdea4ee chỉ cập nhật data/train_batch1.csv.dvc đã tự kích hoạt cả bốn jobs và triển khai thành công.

**Báo cáo chi tiết:** detail.txt được lưu cùng report.json; Bước 3 có precision lớp dương 0.8283, recall 0.6613, FP=17 và FN=42. Với giả định dùng mô hình tìm nhóm thu nhập cao để tiếp cận, FN bỏ sót đối tượng phù hợp nên recall đáng chú ý; FP làm lãng phí lượt tiếp cận. Tỷ lệ lớp dương 24.7842%, chưa vượt mức cảnh báo lệch 5 điểm phần trăm so với 24.8%.
