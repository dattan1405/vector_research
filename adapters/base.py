# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseVectorDB(ABC):
    """
    Interface chuẩn hóa các thao tác cơ bản và truy vấn kết hợp (vector + metadata)
    dành cho các CSDL vector nguồn mở phục vụ kiểm định tính nhất quán.
    """

    @abstractmethod
    def connect(self) -> None:
        """Khởi tạo kết nối tới database."""
        pass

    @abstractmethod
    def init_schema(self, dim: int, recreate: bool = False) -> None:
        """
        Khởi tạo bảng/collection lưu trữ vector và metadata.
        :param dim: Số chiều của vector
        :param recreate: Nếu True sẽ xóa và tạo lại từ đầu
        """
        pass

    @abstractmethod
    def insert(self, record_id: int, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """Thêm mới một bản ghi gồm cả vector và metadata."""
        pass

    @abstractmethod
    def update_metadata(self, record_id: int, metadata: Dict[str, Any]) -> bool:
        """Cập nhật phần metadata của bản ghi."""
        pass

    @abstractmethod
    def update_vector(self, record_id: int, vector: List[float]) -> bool:
        """Cập nhật phần vector của bản ghi."""
        pass

    @abstractmethod
    def update_both(self, record_id: int, vector: List[float], metadata: Dict[str, Any]) -> bool:
        """
        Cập nhật đồng thời cả vector và metadata.
        Đây là thao tác trọng tâm để kiểm tra tính nguyên tử (Atomicity).
        """
        pass

    @abstractmethod
    def delete(self, record_id: int) -> bool:
        """Xóa bản ghi."""
        pass

    @abstractmethod
    def get_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:
        """Lấy chính xác bản ghi theo ID (để đối chiếu trạng thái thực)."""
        pass

    @abstractmethod
    def hybrid_search(self, query_vector: List[float], filter_conditions: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Tìm kiếm xấp xỉ vector kết hợp điều kiện lọc trên metadata (Filtered ANN Search).
        Trả về danh sách kết quả gồm id, score/distance, metadata.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Đóng kết nối."""
        pass
