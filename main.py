from src.processors.batch_processor import process_interview_batch

# Mock JSON input - Format mới
MOCK_JSON_INPUT = {
    "status": "success",
    "interviewer_name": "Unknown",
    "candidate_name": "Danh",
    "position": "Backend Developer",
    "summary": "The interview began with the candidate introducing themselves. Subsequent questions delved into technical differences between Race (likely REST) and GraphQL, and the candidate's approach to resolving team conflicts.",
    "qa_pairs": [
        {
            "question": "Giải thích sự khác biệt giữa var, let và const trong JavaScript?",
            "answer": "var có **phạm vi hàm** và được **hoisted** hoàn toàn. let có **phạm vi khối** và được hoisted một phần (Temporal Dead Zone). const cũng có **phạm vi khối** và ngăn chặn **gán lại** biến (mặc dù thuộc tính của object vẫn có thể thay đổi). Nên dùng **const** theo mặc định, và **let** khi cần gán lại giá trị."
        },
        {
            "question": "Vậy thì Race và grab QR khác nhau như thế nào?",
            "answer": "sử dụng nhiều Android và thường dẫn đến overf fake hoặc underfect và cho phép client yêu cầu chính xác dữ liệu cần thiết"
        },
        {
            "question": "CI/CD là gì và lợi ích của nó?",
            "answer": "CI/CD là viết tắt của **Continuous Integration** và **Continuous Deployment/Delivery**. CI có nghĩa là các developer merge code thường xuyên vào repository chung, kích hoạt **automated tests**. CD tự động hóa quá trình triển khai code lên production. Lợi ích bao gồm **chu kỳ phát hành nhanh hơn**, giảm lỗi thủ công, và **phát hiện bug sớm**."
        }
    ],
    "processed_at": "2025-11-19T13:44:41.259719"
}


def main():
    """Main function"""
    result = process_interview_batch(MOCK_JSON_INPUT)


if __name__ == "__main__":
    main()